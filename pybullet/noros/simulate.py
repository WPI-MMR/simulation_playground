import numpy as np

import time

import os
import pybullet as p
import pinocchio as se3

from pinocchio_bullet_wrapper import PinBulletWrapper


dt = 1e-3
root = os.getcwd()


_urdf_path = lambda fn: root + '/urdf/{}.urdf'.format(fn)



class Solo8Robot(PinBulletWrapper):
	@staticmethod
	def initPhysicsClient():
		physicsClient = p.connect(p.GUI)
		p.setGravity(0,0, -9.81)
		p.setPhysicsEngineParameter(fixedTimeStep=dt, numSubSteps=1)
		return physicsClient

	def __init__(self, physicsClient=None):
		if physicsClient is None:
			self.physicsClient = self.initPhysicsClient()

		# Load the plain.
		plain_urdf = _urdf_path('plane_with_restitution')
		self.planeId = p.loadURDF(plain_urdf)

		# Load the robot
		robotStartPos = [0., 0, 0.40]
		robotStartOrientation = p.getQuaternionFromEuler([0,0,0])

		self.urdf_path = Solo8Config.urdf_path
		self.robotId = p.loadURDF(self.urdf_path, robotStartPos,
			robotStartOrientation, flags=p.URDF_USE_INERTIA_FROM_FILE,
			useFixedBase=False)
		p.getBasePositionAndOrientation(self.robotId)

		# Create the robot wrapper in pinocchio.
		package_dirs = [os.path.dirname(os.path.dirname(self.urdf_path)) + '/urdf']
		self.pin_robot = Solo8Config.buildRobotWrapper()

		# Query all the joints.
		num_joints = p.getNumJoints(self.robotId)

		for ji in range(num_joints):
			p.changeDynamics(self.robotId, ji, linearDamping=.04,
				angularDamping=0.04, restitution=0.0, lateralFriction=0.5)

		self.base_link_name = "base_link"
		controlled_joints = []
		for leg in ['FL', 'FR', 'HL', 'HR']:
			controlled_joints += [leg + '_HFE', leg + '_KFE']
		self.joint_names = controlled_joints


		# Creates the wrapper by calling the super.__init__.
		super(Solo8Robot, self).__init__(self.robotId, self.pin_robot,
			controlled_joints,
			['FL_ANKLE', 'FR_ANKLE', 'HL_ANKLE', 'HR_ANKLE']
		)

	def forward_robot(self, q=None, dq=None):
		if not q:
			q, dq = self.get_state()
		elif not dq:
			raise ValueError('Need to provide q and dq or non of them.')

		self.pin_robot.forwardKinematics(q, dq)
		self.pin_robot.computeJointJacobians(q)
		self.pin_robot.framesForwardKinematics(q)
		self.pin_robot.centroidalMomentum(q, dq)


if __name__ == "__main__":
	# Create a robot instance. This initializes the simulator as well.
	robot = Solo8Robot()
	tau = np.zeros(8)

	# Reset the robot to some initial state.
	q0 = np.matrix(Solo8Config.initial_configuration).T
	dq0 = np.matrix(Solo8Config.initial_velocity).T
	robot.reset_state(q0, dq0)

	# Run the simulator for 100 steps
	for i in range(230):
		# TODO: Implement a controller here.
		robot.send_joint_command(tau)

		# Step the simulator.
		p.stepSimulation()
		# time.sleep(0.001) # You can sleep here if you want to slow down the replay

	# Read the final state and forces after the stepping.
	q, dq = robot.get_state()
	active_eff, forces = robot.get_force()

	print('q', q)
	print('dq', dq)
	print('active eff', active_eff)
	print('forces', forces)