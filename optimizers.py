import torch
from torch.optim import Optimizer, SGD
from oracles import LMO_l1, P_l1

# surrogate for clean imports
SGD = SGD


class PSGDl1(Optimizer):
    """Projected SGD with projection onto l1 norm ball <= lambda_l1"""
    def __init__(self, params, lr, kappa_l1, momentum=0, dampening=0, nesterov=False):
        assert kappa_l1 > 0
        defaults = dict(lr=lr, kappa=kappa_l1, momentum=momentum,
                        dampening=dampening, nesterov=nesterov)
        super(PSGDl1, self).__init__(params, defaults)

    def step(self, closure=None):
        """Performs a single optimization step.

        Arguments:
            closure (callable, optional): A closure that reevaluates the model
                and returns the loss.
        """
        loss = None
        if closure is not None:
            loss = closure()

        for group in self.param_groups:
            kappa = group['kappa']
            momentum = group['momentum']
            dampening = group['dampening']

            for p in group['params']:
                if p.grad is None:
                    continue
                d_p = p.grad.data

                if momentum != 0:
                    param_state = self.state[p]
                    if 'momentum_buffer' not in param_state:
                        buf = param_state['momentum_buffer'] = torch.zeros_like(p.data)
                        buf.mul_(momentum).add_(d_p)
                    else:
                        buf = param_state['momentum_buffer']
                        buf.mul_(momentum).add_(1 - dampening, d_p)
                    d_p = buf

                p.data.add_(-group['lr'], d_p)
                p.data = torch.Tensor(P_l1(p.data.numpy(), kappa))

        return loss


class SGDFWl1(Optimizer):
    """Stochastic Frank Wolfe with |vec(W_i)|_1 <= kappa_l1 where W_i are parameter sets
    """
    def __init__(self, params, kappa_l1):
        self.k = 0
        assert kappa_l1 > 0
        defaults = dict(kappa=kappa_l1)
        super(SGDFWl1, self).__init__(params, defaults)

    def step(self, closure=None):
        """Performs a single optimization step.

        Arguments:
            closure (callable, optional): A closure that reevaluates the model
                and returns the loss.
        """
        loss = None
        if closure is not None:
            loss = closure()

        for group in self.param_groups:
            kappa = group['kappa']

            for p in group['params']:
                if p.grad is None:
                    continue
                s = LMO_l1(p.grad.data.numpy(), kappa)
                gamma = 2 / (self.k + 2)
                # x^(k+1) = x^(k) - g x^(k) + g s
                delta_p = torch.Tensor(gamma * s - gamma * p.data.numpy())
                p.data.add_(delta_p)

        self.k += 1
        return loss
