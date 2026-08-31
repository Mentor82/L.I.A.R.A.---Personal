"""
Auto-imported by Python's `site` module before the sandboxed script runs -
run_sandboxed.sh prepends this file's directory to PYTHONPATH for the python
case only, and `sitecustomize` is a magic module name `site` looks for on
sys.path at interpreter startup (no explicit import needed anywhere).

The sandbox has no DISPLAY, so plt.show() would otherwise just no-op and any
plot the script produces is silently lost. This patches plt.show() to render
each open figure to a PNG in the cwd (the run's workspace/ dir) instead -
the same "capture the current figure as an image" trick Jupyter's own
%matplotlib inline backend has used for years. code_sandbox.py's existing
before/after workspace diff then picks up the new PNG and inlines it as
base64 automatically, so no script (LIARA-authored or hand-written) needs to
know to call savefig() instead of show().
"""
try:
    import matplotlib
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    _plot_counter = [0]

    def _show_as_savefig(*args, **kwargs):
        for num in plt.get_fignums():
            fig = plt.figure(num)
            _plot_counter[0] += 1
            name = "plot.png" if _plot_counter[0] == 1 else f"plot_{_plot_counter[0]}.png"
            fig.savefig(name, dpi=100, bbox_inches="tight")
        plt.close("all")

    plt.show = _show_as_savefig
except ImportError:
    pass
