import numpy as np
from scipy.sparse import issparse
from skglm.solvers.base import BaseSolver
from skglm.solvers.common import construct_grad, construct_grad_sparse
from skglm.utils import prox_vec


class FISTA(BaseSolver):
    r"""ISTA solver with Nesterov acceleration (FISTA).

    This solver implements accelerated proximal gradient descent for linear problems.

    Attributes
    ----------
    max_iter : int, default 100
        Maximum number of iterations.

    tol : float, default 1e-4
        Tolerance for convergence.

    opt_freq : int, default 10
        Frequency for optimality condition check.

    verbose : bool, default False
        Amount of verbosity. 0/False is silent.

    References
    ----------
    .. [1] Beck, A. and Teboulle M.
           "A Fast Iterative Shrinkage-Thresholding Algorithm for Linear Inverse
           problems", 2009, SIAM J. Imaging Sci.
           https://epubs.siam.org/doi/10.1137/080716542
    """

    def __init__(self, max_iter=100, tol=1e-4, opt_freq=10, verbose=0):
        self.max_iter = max_iter
        self.tol = tol
        self.opt_freq = opt_freq
        self.verbose = verbose

    def solve(self, X, y, datafit, penalty, w_init=None, Xw_init=None):
        n_samples, n_features = X.shape
        all_features = np.arange(n_features)
        t_new = 1

        w = w_init.copy() if w_init is not None else np.zeros(n_features)
        z = w_init.copy() if w_init is not None else np.zeros(n_features)
        Xw = Xw_init.copy() if Xw_init is not None else np.zeros(n_samples)

        if hasattr(datafit, "global_lipschitz"):
            lipschitz = datafit.global_lipschitz
        else:
            # TODO: OR line search
            raise Exception("Line search is not yet implemented for FISTA solver.")

        for n_iter in range(self.max_iter):
            t_old = t_new
            t_new = (1 + np.sqrt(1 + 4 * t_old ** 2)) / 2
            w_old = w.copy()
            if issparse(X):
                grad = construct_grad_sparse(
                    X.data, X.indptr, X.indices, y, z, X @ z, datafit, all_features)
            else:
                grad = construct_grad(X, y, z, X @ z, datafit, all_features)
            z -= grad / lipschitz
            w = prox_vec(w, z, penalty, lipschitz)
            Xw = X @ w
            z = w + (t_old - 1.) / t_new * (w - w_old)

            if n_iter % self.opt_freq == 0:
                opt = penalty.subdiff_distance(w, grad, all_features)
                stop_crit = np.max(opt)

                if self.verbose:
                    p_obj = datafit.value(y, w, Xw) + penalty.value(w)
                    print(
                        f"Iteration {n_iter+1}: {p_obj:.10f}, "
                        f"stopping crit: {stop_crit:.2e}"
                    )

                if stop_crit < self.tol:
                    if self.verbose:
                        print(f"Stopping criterion max violation: {stop_crit:.2e}")
                    break
        return w
