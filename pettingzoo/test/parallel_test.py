import random
import warnings

import numpy as np

from pettingzoo.utils.conversions import (aec_to_parallel_wrapper, parallel_to_aec_wrapper,
                                          turn_based_aec_to_parallel_wrapper)
from pettingzoo.utils.wrappers import BaseWrapper

from .api_test import missing_attr_warning


def sample_action(env, obs, agent):
    agent_obs = obs[agent]
    if isinstance(agent_obs, dict) and "action_mask" in agent_obs:
        legal_actions = np.flatnonzero(agent_obs["action_mask"])
        if len(legal_actions) == 0:
            return 0
        return random.choice(legal_actions)
    return env.action_space(agent).sample()


def parallel_api_test(par_env, num_cycles=1000):
    par_env.max_cycles = num_cycles

    if not hasattr(par_env, 'possible_agents'):
        warnings.warn(missing_attr_warning.format(name='possible_agents'))

    assert not isinstance(par_env.unwrapped, aec_to_parallel_wrapper)
    assert not isinstance(par_env.unwrapped, parallel_to_aec_wrapper)
    assert not isinstance(par_env.unwrapped, turn_based_aec_to_parallel_wrapper)
    assert not isinstance(par_env.unwrapped, BaseWrapper)
    MAX_RESETS = 2
    for _ in range(MAX_RESETS):
        obs = par_env.reset()
        assert isinstance(obs, dict)
        assert set(obs.keys()) == (set(par_env.agents))
        done = {agent: False for agent in par_env.agents}
        live_agents = set(par_env.agents[:])
        has_finished = set()
        for _ in range(num_cycles):
            actions = {agent: sample_action(par_env, obs, agent) for agent in par_env.agents if agent in done and not done[agent]}
            obs, rew, done, info = par_env.step(actions)
            for agent in par_env.agents:
                assert agent not in has_finished, "agent cannot be revived once done"

                if agent not in live_agents:
                    live_agents.add(agent)

            assert isinstance(obs, dict)
            assert isinstance(rew, dict)
            assert isinstance(done, dict)
            assert isinstance(info, dict)

            agents_set = set(live_agents)
            keys = 'observation reward done info'.split()
            vals = [obs, rew, done, info]
            for k, v in zip(keys, vals):
                key_set = set(v.keys())
                if key_set == agents_set:
                    continue
                if len(key_set) < len(agents_set):
                    warnings.warn('Live agent was not given {}'.format(k))
                else:
                    warnings.warn('Agent was given {} but was done last turn'.format(k))

            if hasattr(par_env, 'possible_agents'):
                assert set(par_env.agents).issubset(set(par_env.possible_agents)), "possible_agents defined but does not contain all agents"

                has_finished |= {agent for agent, d in done.items() if d}
                if not par_env.agents and has_finished != set(par_env.possible_agents):
                    warnings.warn('No agents present but not all possible_agents are done')
            elif not par_env.agents:
                warnings.warn('No agents present')

            for agent in par_env.agents:
                assert par_env.observation_space(agent) is par_env.observation_space(agent), "observation_space should return the exact same space object (not a copy) for an agent. Consider decorating your observation_space(self, agent) method with @functools.lru_cache(maxsize=None)"
                assert par_env.action_space(agent) is par_env.action_space(agent), "action_space should return the exact same space object (not a copy) for an agent (ensures that action space seeding works as expected). Consider decorating your action_space(self, agent) method with @functools.lru_cache(maxsize=None)"

            for agent, d in done.items():
                if d:
                    live_agents.remove(agent)

            assert set(par_env.agents) == live_agents

            if len(live_agents) == 0:
                break
