import argparse


def argparser(N=10000, until=100, sim_type="time", remote=0):
    parser = argparse.ArgumentParser()

    parser.add_argument("-N", type=int, default=N, help="Number of entities")
    parser.add_argument(
        "-r", "--remote", type=int, default=remote, help="Switch for remote simulators"
    )
    parser.add_argument("--plot", type=int, default=0)
    parser.add_argument("-d", "--debug", type=int, help="Switch for debug")
    parser.add_argument("-c", "--cache", type=int, help="Switch for cache")
    parser.add_argument(
        "-u", "--until", type=int, default=until, help="Simulation length"
    )
    parser.add_argument(
        "-t",
        "--sim-type",
        type=str,
        default=sim_type,
        choices=["time", "t", "event", "e"],
        help="Simulator type",
    )
    parser.add_argument("-l", "--lazy_stepping", type=int)
    parser.add_argument(
        "--compare",
        type=int,
        default=0,
        help="Compare execution graph with previously stored version",
    )
    args = parser.parse_args()

    world_args = ["debug", "cache"]
    world_args = {
        arg: getattr(args, arg) for arg in world_args if getattr(args, arg) is not None
    }

    optional_run_args = ["until", "lazy_stepping"]
    run_args = {
        arg: getattr(args, arg)
        for arg in optional_run_args
        if getattr(args, arg) is not None
    }

    if args.sim_type == "t":
        args.sim_type = "time"
    elif args.sim_type == "e":
        args.sim_type = "event"

    return args, world_args, run_args
