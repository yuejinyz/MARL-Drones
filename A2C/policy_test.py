import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.autograd import Variable
import numpy as np
from models import Policy
from torch.distributions import Categorical
from noVis_sim import DroneEnv
import argparse


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif v.lower() in ("no", "false", "f", "n", "0"):
        return False
    else:
        raise argparse.ArgumentTypeError("Boolean value expected.")


parser = argparse.ArgumentParser(description="A2C Policy test")
parser.add_argument("--policy", type=str, default="MLP", help="CNN, MLP, Attn policy")
parser.add_argument("--grid_size", type=int, default=5, help="Grid size, Default: 5x5")
parser.add_argument("--n_drones", type=int, default=3, help="number of drones")
parser.add_argument(
    "--n_anamolous",
    type=int,
    default=5,
    help="number of anomalous cells in environment",
)
parser.add_argument(
    "--enable_icm", type=str2bool, default=False, help="use intrinsic curiosity module"
)

args = parser.parse_args()
icm_model_name = "ICM_" if args.enable_icm else ""


def prepare_inputs(args, obs, drone_pos, n_drones, obs_size):
    if args.policy == "MLP":
        obs = np.reshape(obs, [1, obs_size])
        obs = Variable(torch.from_numpy(obs).float())

    if args.policy == "CNN" or args.policy == "Attn":
        obs = np.reshape(obs, [1, args.grid_size, args.grid_size])
        obs = Variable(torch.from_numpy(obs).float())

    drone_pos = drone_pos.reshape((n_drones, 2))
    drone_pos = Variable(torch.from_numpy(drone_pos).float().view(1, -1))
    return obs, drone_pos


def load_models(args, state_size, n_drones, action_size):
    nets = []
    for i in range(n_drones):
        model = Policy(state_size, n_drones, action_size, policy_type=args.policy)
        model.load_state_dict(
            torch.load(
                f"A2C_models/{args.policy}_policy/A2C_drone_{icm_model_name}{i}.bin"
            )
        )
        nets.append(model)
    return nets


env = DroneEnv(
    row_count=args.grid_size,
    col_count=args.grid_size,
    step_size=1.0,
    n_anamolous=args.n_anamolous,
    n_drones=args.n_drones,
)

obs_size = env.state_size
action_size = env.action_size
n_drones = env.n_drones

nets = load_models(args, obs_size, n_drones, action_size)
print("models loaded")

obs = env.reset()
drone_pos = np.array(env.n_drones_pos)
obs, drone_pos = prepare_inputs(args, obs, drone_pos, n_drones, obs_size)
done = False

step = 0
print(f"Step: {step+1}")
print(f"Drone positions:{env.n_drones_pos}")
temp_st = obs.reshape((5, 5))
print(temp_st, "\n")

while not done:

    policies = []
    values = []
    actions = []
    for i in range(n_drones):
        p, v = nets[i](obs, drone_pos)
        probs = F.softmax(p, dim=-1)
        a = Categorical(probs).sample()[0]

        policies.append(p)
        values.append(v)
        actions.append(a.numpy())

    obs, reward, done = env.step(actions)
    drone_pos = np.array(env.n_drones_pos)
    obs, drone_pos = prepare_inputs(args, obs, drone_pos, n_drones, obs_size)

    if (step + 1) % 100 == 0:
        print(f"Step: {step+1}")
        print(f"Drone positions:{env.n_drones_pos}")
        print(f"Action:{actions}")
        temp_st = obs.reshape((5, 5))
        print(temp_st, "\n")

    step += 1
