#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Feb 18 17:38:53 2020

@author: martafradera
"""

import gym
import neurogym as ngym
import numpy as np


class Shaping(ngym.TrialWrapper):
    metadata = {
        'description': '',
        'paper_link': None,
        'paper_name': None,
    }

    def __init__(self, env, init_ph=0, max_num_reps=3, short_dur=2, th=0.8,
                 perf_w=1000):
        """
        """
        super().__init__(env)
        self.env = env
        self.curr_ph = init_ph
        self.curr_perf = 0
        self.perf_window = perf_w
        self.goal_perf = [th]*4
        self.mov_window = []
        self.counter = 0
        self.action = 0
        self.prev_act = 0
        self.max_num_reps = max_num_reps
        self.first_choice = True
        self.performance = 0
        self.short = False
        self.variable = True
        self.short_dur = int(short_dur*self.env.dt)
        self.ori_timing = self.env.timing
        self.ori_periods = self.env.timing.copy()
        self.sigma_dt_ori = self.env.sigma_dt

    def count(self, action):
        '''
        check the last three answers during stage 0 so the network has to
        alternate between left and right
        '''
        if action != 0:
            if action == self.prev_act:
                self.counter += 1
            else:
                self.counter = 1
                self.prev_act = action

    def set_phase(self):
        if self.curr_ph < 4:
            if len(self.mov_window) >= self.perf_window:
                self.mov_window.append(self.performance)
                self.mov_window.pop(0)  # remove first value
                self.curr_perf = np.mean(self.mov_window)
                if self.curr_perf >= self.goal_perf[self.curr_ph]:
                    self.curr_ph += 1
                    self.mov_window = []
            else:
                self.mov_window.append(self.performance)

    def new_trial(self, **kwargs):
        self.set_phase()
        print('curr_ph: ', self.curr_ph)
        self.first_choice = True
        self.performance = 0
        self.change_periods = list(self.ori_timing.keys())[:-1]
        # this is done in the step function in core that we have overwritten
        self.env.performance = 0
        self.env.t = self.env.t_ind = 0
        self.env.num_tr += 1

        if self.curr_ph < 2:
            self.env.sigma_dt = 0
            if not self.short:
                print('ori: ', self.env.timing)
                self.short = True
                self.variable = False
                for key, val in self.ori_periods.items():
                    if key in self.change_periods:
                        dist, args = val
                        self.env.timing[key] = ('constant', self.short_dur)
                print('new: ', self.env.timing)

        elif self.curr_ph == 2:
            self.env.sigma_dt = 0
            if not self.short or not self.variable:
                print('ori: ', self.env.timing)
                self.short = True
                self.variable = True
                for key, val in self.ori_periods.items():
                    if key in self.change_periods:
                        dist, args = val
                        if dist != 'constant':
                            factor = self.short_dur/args[0]
                            self.env.timing[key] =\
                                (dist, [int(n*factor/self.env.dt)*self.env.dt
                                        for n in args])
                        else:
                            self.env.timing[key] = ('constant', self.short_dur)
                print('new: ', self.env.timing)

        else:
            self.env.sigma_dt = self.sigma_dt_ori
            print('ori: ', self.env.timing)
            print('new: ', self.env.timing)

        self.env.new_trial()

    def step(self, action):
        if self.curr_ph < 2:
            obs, reward, done, info = self.env._step(action)
            self.env.t += self.env.dt  # increment within trial time count
            self.env.t_ind += 1
            if info['new_trial']:
                if self.curr_ph == 0:
                    # reward when action != fixate
                    # agent cannot go max_num_reps times in a row to same side
                    self.count(action)
                    if self.counter > self.max_num_reps:
                        reward = 0
                        self.performance = 0
                    else:
                        reward = self.env.rewards['correct']
                        self.performance = 1
                elif self.curr_ph == 1:
                    if not self.env.performance:
                        reward = 0
                        info['new_trial'] = False
                    if self.first_choice:
                        self.performance = self.env.performance
                        self.first_choice = False

            if self.env.t > self.env.tmax - self.env.dt and\
               not info['new_trial']:
                info['new_trial'] = True
                reward += self.r_tmax
                info['performance'] = self.performance

            if info['new_trial']:
                info['performance'] = self.performance
                self.new_trial()
        else:
            obs, reward, done, info = self.env.step(action)
            if self.curr_ph == 2:
                reward = max(reward, 0)
            if info['new_trial']:
                self.performance = info['performance']
                self.new_trial()

        return obs, reward, done, info


if __name__ == '__main__':
    import neurogym as ngym

    task = 'PerceptualDecisionMaking-v0'
    env = gym.make(task)
    env = Shaping(env, init_ph=2, short_dur=3, th=0.1, perf_w=2)
    # env.seed(0)
    ngym.utils.plot_env(env, num_steps_env=100)  # , def_act=0)