#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Mar  4 12:41:52 2019

@author: molano
"""

from gym.core import Wrapper
import os
import numpy as np
import analysis


class manage_data(Wrapper):
    """
    modfies a given environment by changing the probability of repeating the
    previous correct response
    """
    def __init__(self, env, inst=0, plt_tr=True, folder=None):
        Wrapper.__init__(self, env=env)
        self.num_tr = 0
        self.env = env
        self.inst = inst
        self.action_space = self.env.action_space
        self.observation_space = self.env.observation_space
        # data to save
        self.choice_mat = []
        self.side_mat = []
        self.rep_prob_mat = []
        self.stim_mat = []
        self.cum_obs = 0
        # for rendering
        self.obs_mat = []
        self.act_mat = []
        self.rew_mat = []
        self.max_num_samples = 200
        self.num_subplots = 3
        self.plt_tr = plt_tr
        if self.plt_tr:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            self.fig, self.ax = plt.subplots(self.num_subplots, 1)
        if folder is not None:
            self.folder = folder + '/'
        else:
            self.folder = "../tmp/"
        if not os.path.exists(self.folder):
            os.mkdir(self.folder)
        # seeding
        self.env.seed()
        self.saving_name = self.folder +\
            self.env.__class__.__name__ + str(self.inst)

    def reset(self):
        if len(self.rew_mat) > 0 and self.inst == 0:
            data = {'choice': self.choice_mat, 'stimulus': self.stim_mat,
                    'correct_side': self.side_mat, 'obs_mat': self.obs_mat,
                    'act_mat': self.act_mat, 'rew_mat': self.rew_mat,
                    'rep_prob': self.rep_prob_mat}
            np.savez(self.saving_name + '_bhvr_data_' +
                     str(self.num_tr) + '.npz', **data)
            self.choice_mat = []
            self.side_mat = []
            self.rep_prob_mat = []
            self.stim_mat = []
            self.obs_mat = []
            self.act_mat = []
            self.rew_mat = []
            if len(self.side_mat) != 0:
                try:
                    analysis.no_stim_analysis(file=self.saving_name +
                                              '_data.npz',
                                              save_path=self.saving_name,
                                              figs=self.plt_tr)
                except Exception:
                    print('could not perform the analysis')
            if self.plt_tr:
                self.render()

        self.obs_mat = []
        self.act_mat = []
        self.rew_mat = []
        return self.env.reset()

    def step(self, action):
        obs, rew, done, info = self.env.step(action)
        self.cum_obs += obs
        if 'new_trial' in info.keys():
            self.num_tr += 1
            self.choice_mat.append(action)
            self.stim_mat.append(self.cum_obs)
            self.cum_obs = 0
            if 'gt' in info.keys():
                self.side_mat.append(info['gt'])
            if 'rep_prob' in info.keys():
                self.rep_prob_mat.append(info['rep_prob'])

        self.store_data(obs, action, rew)
        return obs, rew, done, info

    def render(self, mode='human'):
        """
        plots relevant variables/parameters
        """
        # observations
        obs = np.array(self.obs_mat)
        self.ax[0].imshow(obs.T, aspect='auto')
        self.ax[0].set_ylabel('obs')
        self.ax[0].set_xticks([])
        self.ax[0].set_yticks([])
        # actions
        self.ax[1].plot(np.arange(1, len(self.act_mat)+1)+0.5, self.act_mat)
        self.ax[1].set_ylabel('action')
        self.ax[1].set_xlim([0, self.max_num_samples+0.5])
        self.ax[1].set_xticks([])
        self.ax[1].set_yticks([])
        # reward
        self.ax[2].plot(np.arange(1, len(self.act_mat)+1)+0.5, self.rew_mat)
        self.ax[2].set_ylabel('reward')
        self.ax[2].set_xlim([0, self.max_num_samples+0.5])
        if self.inst == 0:
            self.fig.savefig(self.saving_name + '_trials.png')
        self.ax[0].cla()
        self.ax[1].cla()
        self.ax[2].cla()

    def store_data(self, obs, action, rew):
        if len(self.rew_mat) < self.max_num_samples:
            self.obs_mat.append(obs)
            self.act_mat.append(action)
            self.rew_mat.append(rew)
