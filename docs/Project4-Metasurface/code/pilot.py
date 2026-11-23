import sys
sys.path.insert(0,'Project4-Metasurface/code')
from wave_fem import *
from scipy.optimize import minimize
from dataclasses import replace
for chi in [0,.05]:
 m=WaveFEM(Config(chi=chi),3);cache={}
 def ev(c):
  if 'x' not in cache or not np.array_equal(cache['x'],c):cache.update(x=c.copy(),v=m.evaluate(c))
  return cache['v']
 c=np.ones(20); print('INITIAL',chi,{k:ev(c)[k] for k in ['objective','constraints','energy']},flush=True)
 r=minimize(lambda c:ev(c)['objective'],c,jac=lambda c:ev(c)['gradient'],bounds=[(.5,2.5)]*20,constraints=[dict(type='ineq',fun=lambda c:ev(c)['constraints'],jac=lambda c:ev(c)['constraint_jacobian'])],method='SLSQP',options=dict(maxiter=400,ftol=1e-11))
 print('FINAL',chi,r.success,r.message,r.nit,r.fun,ev(r.x)['constraints'],r.x,flush=True)
