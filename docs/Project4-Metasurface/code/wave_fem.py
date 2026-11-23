"""Own P1 Galerkin solver for a split, nonlinear loaded transmission line.
Complex phasors use exp(+i wt); derivatives/adjoints are real, not holomorphic.
"""
from dataclasses import dataclass
import numpy as np
from scipy.sparse import coo_matrix, bmat, csc_matrix
from scipy.sparse.linalg import spsolve

@dataclass(frozen=True)
class Config:
    length: float = .36
    cells: int = 20
    switch_cell: int = 6
    alpha: float = .03
    beta: float = 2*np.pi
    chi: float = .05
    energy_limit: float = 1.6
    regularization: float = .002
    z_on: complex = .02+.04j
    z_off: complex = .02-4j

class WaveFEM:
    def __init__(self, config=Config(), per_cell=4):
        self.cfg=config; self.per_cell=per_cell
        ne=config.cells*per_cell; split=config.switch_cell*per_cell
        base=np.linspace(0,config.length,ne+1)
        self.x=np.insert(base,split,base[split]); self.n=len(self.x)-1
        self.edges=np.array([(e,e+1) if e<split else (e+1,e+2) for e in range(ne)])
        self.left,self.right=split,split+1
        self.h=config.length/ne; self.cell=np.arange(ne)//per_cell
        t,w=np.polynomial.legendre.leggauss(4)
        self.N=np.column_stack(((1-t)/2,(1+t)/2)); self.w=w*self.h/2
        self.M=np.einsum('q,qi,qj->ij',self.w,self.N,self.N)
        self.K=np.array([[1,-1],[-1,1]])/self.h
        self.rows=np.repeat(self.edges,2,axis=1).ravel()
        self.cols=np.tile(self.edges,(1,2)).ravel()
        self.solve_count=0; self.adjoint_count=0
    def sparse(self,a):
        return coo_matrix((a.ravel(),(self.rows,self.cols)),shape=(self.n+1,self.n+1)).tocsc()[:self.n,:self.n]
    def linear(self,c,state):
        z=self.cfg.alpha+1j*self.cfg.beta
        y=self.cfg.alpha+1j*self.cfg.beta*np.asarray(c)[self.cell]
        A=self.sparse(self.K[None,:,:]/z+y[:,None,None]*self.M)
        ids=[0,self.left,self.right,self.left,self.right]
        js=[0,self.left,self.right,self.right,self.left]
        zs=(self.cfg.z_on,self.cfg.z_off)[state]
        return A+coo_matrix(([1,1/zs,1/zs,-1/zs,-1/zs],(ids,js)),shape=A.shape).tocsc()
    def unpack(self,u):
        return np.r_[u[:self.n]+1j*u[self.n:],0j]
    def residual_jacobian(self,u,c,state,A=None,load=None):
        if A is None:A=self.linear(c,state)
        V=self.unpack(u); v=V[self.edges]@self.N.T
        k=1j*self.cfg.beta*self.cfg.chi
        nl=k*np.einsum('q,qi,eq->ei',self.w,self.N,abs(v)**2*v)
        f=A@V[:-1]
        np.add.at(f,self.edges.ravel()[self.edges.ravel()<self.n],nl.ravel()[self.edges.ravel()<self.n])
        f[0]-=2
        if load is not None:f-=load
        aa=v.real;bb=v.imag
        dx=k*((3*aa*aa+bb*bb)+2j*aa*bb)
        dy=k*(2*aa*bb+1j*(aa*aa+3*bb*bb))
        B=self.sparse(np.einsum('q,qi,qj,eq->eij',self.w,self.N,self.N,dx))
        C=self.sparse(np.einsum('q,qi,qj,eq->eij',self.w,self.N,self.N,dy))
        J=bmat([[A.real+B.real,-A.imag+C.real],[A.imag+B.imag,A.real+C.imag]],format='csc')
        return np.r_[f.real,f.imag],J
    def solve(self,c,state,load=None):
        self.solve_count+=1; A=self.linear(c,state)
        rhs=np.zeros(self.n,complex);rhs[0]=2
        if load is not None:rhs+=load
        V=spsolve(A,rhs);u=np.r_[V.real,V.imag]; hist=[]
        for it in range(45):
            f,J=self.residual_jacobian(u,c,state,A,load);r=np.linalg.norm(f,np.inf);hist.append(float(r))
            if r<2e-11:return u,J,hist
            d=spsolve(J,-f);step=1.
            for _ in range(22):
                un=u+step*d
                fn,_=self.residual_jacobian(un,c,state,A,load)
                if np.linalg.norm(fn)<(1-1e-4*step)*np.linalg.norm(f):break
                step*=.5
            else:raise RuntimeError('Newton line search failed')
            u=un
        raise RuntimeError('Newton iteration limit')
    def parameter_jacobian(self,u):
        v=self.unpack(u)[self.edges]@self.N.T
        local=1j*self.cfg.beta*np.einsum('q,qi,eq->ei',self.w,self.N,v)
        P=np.zeros((self.n,self.cfg.cells),complex)
        for e,(a,b) in enumerate(self.edges):
            P[a,self.cell[e]]+=local[e,0]
            if b<self.n:P[b,self.cell[e]]+=local[e,1]
        return np.vstack((P.real,P.imag))
    def energy(self,u):
        V=self.unpack(u);v=V[self.edges]@self.N.T
        value=np.sum(self.w*abs(v)**2)/self.cfg.length
        local=2*np.einsum('q,qi,eq->ei',self.w,self.N,v)/self.cfg.length
        g=np.zeros(self.n+1,complex);np.add.at(g,self.edges.ravel(),local.ravel())
        return float(value),np.r_[g[:-1].real,g[:-1].imag]
    def evaluate(self,c,grad=True):
        solutions=[self.solve(c,s) for s in (0,1)]
        R=[self.unpack(t[0])[0]-1 for t in solutions];S=sum(R)
        energy=[self.energy(t[0]) for t in solutions]
        # All inequality functions use g >= 0.
        objective=abs(S)**2+self.cfg.regularization*np.mean((np.asarray(c)-1)**2)
        constraints=np.array([abs(R[0])**2-.64,abs(R[1])**2-.64,self.cfg.energy_limit-energy[0][0],self.cfg.energy_limit-energy[1][0]])
        G=np.zeros((5,self.cfg.cells));G[0]=2*self.cfg.regularization*(np.asarray(c)-1)/self.cfg.cells
        if grad:
            for s,(u,J,hist) in enumerate(solutions):
                Q=np.zeros((2*self.n,5));Q[0,0]=2*S.real;Q[self.n,0]=2*S.imag
                Q[0,1+s]=2*R[s].real;Q[self.n,1+s]=2*R[s].imag
                Q[:,3+s]=-energy[s][1]
                lam=spsolve(J.T,Q);self.adjoint_count+=5
                G-=lam.T@self.parameter_jacobian(u)
        return dict(objective=float(objective),phase_objective=float(abs(S)**2),constraints=constraints,gradient=G[0],constraint_jacobian=G[1:],R=R,energy=[e[0] for e in energy],solutions=solutions)
    def power_balance(self,u,state):
        V=self.unpack(u);I=-np.diff(V[self.edges],axis=1).ravel()/self.h/(self.cfg.alpha+1j*self.cfg.beta)
        v=V[self.edges]@self.N.T
        line=self.cfg.alpha*(np.sum(self.w*abs(v)**2)+self.h*np.sum(abs(I)**2))
        zs=(self.cfg.z_on,self.cfg.z_off)[state];Is=(V[self.left]-V[self.right])/zs
        switch=zs.real*abs(Is)**2; incoming=1-abs(V[0]-1)**2
        return dict(incoming=float(incoming),line_loss=float(line),switch_loss=float(switch),defect=float(incoming-line-switch))
