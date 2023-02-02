# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/08_agent.ipynb.

# %% auto 0
__all__ = ['Agent', 'AgentObjective']

# %% ../nbs/08_agent.ipynb 4
from typing import Callable, Tuple, List, Optional

import torch
from torch import nn
import torch.nn.functional as F
from torch.nn.utils.rnn import pad_sequence
from torch.distributions import Categorical

from transformers import AutoModel
import pytorch_lightning as pl 
from torchtyping import TensorType

from .utils import ReplayBuffer

# %% ../nbs/08_agent.ipynb 6
class Agent(nn.Module):
    "The RL-based language model."
    def __init__(
        self,
        model: Callable # a pre-trained `transformers` model
    ):
        super().__init__()
        n_embd = model.config.n_embd
        self.eos_token_id = model.config.eos_token_id

        self.policy_network = model        
        self.value_network = nn.Sequential(
            nn.Linear(n_embd, 256),
            nn.ReLU(),
            nn.Linear(256, 256),
            nn.ReLU(),
            nn.Linear(256, 1),
            nn.Tanh()
        )
    
    def get_value(
        self, hidden_state: TensorType["batch_size", "seq_len", "n_embd"]
    ) -> TensorType["batch_size", 1]:
        """Get value from the value network."""
        return self.value_network(hidden_state)[:, -1, :]

    def generate(
        self,
        input_ids: TensorType["batch_size", "seq_len"],
        attention_mask: Optional[TensorType["batch_size", "seq_len"]] = None,
        **kwargs
    ) -> TensorType["batch_size", "seq_len"]:
        output = self.policy_network.generate(
            input_ids=input_ids, attention_mask=attention_mask, **kwargs
        )
        return output
    
    def forward(
        self,
        input_ids: TensorType["batch_size", "seq_len"], # input_ids
        attention_mask: Optional[TensorType["batch_size, seq_len"]] = None
    ) -> Tuple[
        TensorType["batch_size", "seq_len", "vocab_size"],
        TensorType["batch_size", "seq_len", "vocab_size"],
        TensorType["batch_size", "seq_len"],
        TensorType["batch_size", 1]
    ]: # action, logprobs, entropy, value
        """_summary_"""
        if attention_mask is None:
            base_output = self.policy_network(
                input_ids,
                output_hidden_states=True,
            )
        else:
            base_output = self.policy_network(
                input_ids, attention_mask=attention_mask,
                output_hidden_states=True,
            )
        
        last_hidden_state = base_output.hidden_states[-1]
        
        # takes the logit of the last token
        # for each sequence in the batch
        logits = base_output.logits[:, -1, :]
        probs = F.softmax(logits, dim=-1)
                                
        action_dist = Categorical(probs=probs)
        action = action_dist.sample()
        entropy = action_dist.entropy()
        logprobs = action_dist.log_prob(action)
        
        # predicted reward value
        value = self.get_value(last_hidden_state).squeeze(-1)
        
        return action, logprobs, entropy, value

# %% ../nbs/08_agent.ipynb 12
class AgentObjective(nn.Module):
    """Agent objective."""
    def __init__(
        self,
        model: Callable, # the language model
        sft_model: Callable, # the reference model
        reward_model: Callable, # the reward model
        gamma: float,
        beta: float
    ):
        super().__init__()
        self.model = model
        self.sft_model = sft_model
        self.reward_model = reward_model
        self.gamma = gamma
        self.beta = beta
        
    def forward(
        self,
        input_ids: TensorType["batch_size", "seq_len"],
        attention_mask: TensorType["batch_size", "seq_len"]
    ) -> TensorType[1]: # A scalar objective value
        """Calculate the objective value given the input ids and attention mask."""
        model_logits = self.model(input_ids, attention_mask)
        
        model_dist = F.softmax(model_logits, dim=-1)
        
        sft_logits = self.sft_model(input_ids, attention_mask)
        sft_dist = F.softmax(sft_logits, dim=-1)
        
        reward_score = self.reward_model(input_ids, attention_mask)
        
        ratio = torch.log(model_dist / sft_dist)
        
        # compute the coherent of the generated text
        coherent = torch.log(model_dist)
        
        objective = (reward_score - self.beta*ratio).mean() + self.gamma * coherent.mean()
        
        return objective
