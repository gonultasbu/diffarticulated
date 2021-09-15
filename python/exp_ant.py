#!/usr/bin/python
#
# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Lint as: python3
"""Example how to use differentiable physics engine using python.

We used pybind11 to expose the classes of pydiffphys.
At the moment, only double precision version is exposed.
Will also expose stan_math forward mode differentiation, dual and fixed point.
"""

from absl import app
from absl import flags

import torch
import pytinydiffsim as pd
import api_diff
import numpy as np
import time

FLAGS = flags.FLAGS

def get_loss(joints, target_joint, init_tau):
  return ((joints[3:6]-target_joint)**2)[0] #+ 0.02 * init_tau.norm()


def main(argv):
  if len(argv) > 1:
    raise app.UsageError("Too many command-line arguments.")

  world = pd.TinyWorld(do_vis=True)
  world.friction = pd.Utils.scalar_from_double(0.002)
  parser = pd.TinyUrdfParser()
  convert_tool = pd.UrdfToMultiBody2()

  mb_box1 = world.create_multi_body()
  mb_box1.isFloating = False
  urdf_structures = parser.load_urdf('./data/plane_implicit.urdf')

  convert_tool.convert2(urdf_structures, world, mb_box1)


  mb_sphere = world.create_multi_body()
  mb_sphere.isFloating = True
  urdf_structures = parser.load_urdf('./data/ant_torso1.urdf')
  convert_tool.convert2(urdf_structures, world, mb_sphere)

  print(mb_sphere.dof_u())
  print(mb_sphere.dof())
  print(mb_sphere.dof_qd())
  print(mb_sphere.dof_state())

  world.friction = pd.Utils.scalar_from_double(0.002)
  # world.restitution = pd.Utils.scalar_from_double(0.6)friction

  knee_angle = -0.5
  abduction_angle = 0.2
  init_q = torch.tensor([0.0,0.0,0.0,1.0, 0.0,0.0,0.75, 0,0,0,0,0,-0,0,-0], dtype=torch.float32, requires_grad=True)
  init_qd = torch.zeros([8+6], dtype=torch.float32, requires_grad=False)

  grav = pd.TinyVector3(pd.Utils.zero(), pd.Utils.zero(), pd.Utils.scalar_from_double(-9.81))

  dt = 1/1000.
  finer = 1
  world.dt = pd.Utils.scalar_from_double(dt/finer)
  n_step = 1000
  dof_u = 8
  n = dof_u * n_step
  init_tau = torch.normal(mean=0, std=1,
    size=(n_step, dof_u), dtype=torch.float32, requires_grad=True)
  
  # target_joint = torch.tensor([0.98, 0, 0.2], dtype=torch.float32, requires_grad=True)
  
  world.adj_initialize(grav, n_step, dof_u)
  optimizer = torch.optim.Adam([init_tau], lr=0.01)
  frameskip_gfx_sync = 128

  for steps in range(1000):
    sync_counter = 0
    optimizer.zero_grad()
    q, qd = init_q, init_qd
    for sim_step in range(n_step):
      tau = init_tau[sim_step]
      q, qd = api_diff.sim_layer(q, qd, tau, world)
      
    

    joints = api_diff.get_joints(q, world)
   
    
    loss = joints.sum()
    print(steps, " loss =", loss)


    loss.backward()

    if loss.detach().numpy() < 1e-4:
      print(steps)
      break

    # optimizer.step()
    # world.friction = pd.Utils.scalar_from_double(2)
  print("done")
  print('tau=',init_tau.reshape([-1,5]))
  print(init_tau.min(), init_tau.max())
  # np.save('./data/push/tau.npy', init_tau.reshape([-1,5]).detach().numpy())
  


if __name__ == "__main__":
  app.run(main)
