from . import base

class DerivedParameterTest(base.DerivedParameter):
    content = 'test'

#--------------------------------------------
class DP_TEST1(DerivedParameterTest):
    rootparams = ['TEPHIN']
    timestep = 32.8

    def calc(self, dataset):
        return dataset['TEPHIN'].vals

class DP_TEST2(DerivedParameterTest):
    rootparams = ['TEPHIN']
    timestep = 65.6

    def calc(self, dataset):
        return dataset['TEPHIN'].vals * 1.5

class DP_TEST3(DerivedParameterTest):
    rootparams = ['TEPHIN']
    timestep = 65.6

    def calc(self, dataset):
        return dataset['TEPHIN'].vals * 2.0

