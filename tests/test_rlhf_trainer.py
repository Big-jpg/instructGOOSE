import torch
from torch.utils.data import DataLoader

from transformers import AutoModelForCausalLM

from instruct_goose.agent import Agent
from instruct_goose.dataset import PromptDataset
from instruct_goose.trainer import RLHFTrainer
from instruct_goose.utils import create_reference_model, RLHFConfig

def test_create_rlhf_trainer(agent_model):
    config = RLHFConfig()

    model = Agent(agent_model)
    ref_model = create_reference_model(model)

    trainer = RLHFTrainer(model, ref_model, config)

    assert trainer.model != None
    assert isinstance(trainer.epsilon, (int, float))

# def test_rlhf_trainer_with_ref_model(default_config, small_prompt_dataset, agent_tokenizer):
#     # TODO: implement
#     model_checkpoint = default_config["model"]["model_path"]

#     config = {
#         "epislon": 0.01,
#         "ent_coef": 0.01,
#         "vf_coef": 0.5
#     }

#     model = Agent(model_checkpoint)
#     ref_model = create_reference_model(model)

#     ppo_trainer = RLHFTrainer(model, ref_model, config)

#     prompt_dataset = PromptDataset(small_prompt_dataset)
#     dataloader = DataLoader(prompt_dataset, batch_size=2, shuffle=True)

#     losses = []
#     objectives = []

#     for batch in dataloader:
#         loss, objective = ppo_trainer.step(
#             input_ids=batch["input_ids"],
#             attention_mask=batch["attention_mask"]
#         )

#         losses.append(loss)
#         objectives.append(objective)

#     assert isinstance(loss)
#     assert loss.shape == (1,)
#     assert isinstance(loss, torch.Tensor)
#     assert objective.shape == (1,)

def test_compute_advantage_and_return_rlhf_trainer():
    rewards = torch.tensor([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
    values = torch.tensor([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])

    advantages, returns = RLHFTrainer.compute_advantage_and_return(rewards, values)

    assert advantages.shape == (1,)
    assert returns.shape == (rewards.shape[-1],)

def test_compute_loss_rlhf_trainer(agent_model, agent_tokenizer):
    config = RLHFConfig()
    model = Agent(agent_model)
    ref_model = create_reference_model(model)
    trainer = RLHFTrainer(model, ref_model, config)

    queries = [
        "Are you a nice bot?",
        "What time is it?"
    ]
    responses = [
        "Nah. I'm a mean bot.",
        "Nah. I'm not telling you!!!"
    ]

    query_input_ids = agent_tokenizer(queries, padding=True, truncation=True, return_tensors="pt")["input_ids"]
    response_input_ids = agent_tokenizer(responses, padding=True, truncation=True, return_tensors="pt")["input_ids"]
    rewards = torch.tensor([0.1, 0.9])

    loss = trainer.compute_loss(query_input_ids, response_input_ids, rewards)

    assert isinstance(loss.item(), (int, float))