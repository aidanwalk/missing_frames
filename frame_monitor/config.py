import argparse

parser = argparse.ArgumentParser(description="Monitor frame timing from FITS files")
parser.add_argument(
    "--data-dir", "-d", type=str,
    default="./data/",
    help="Directory to watch for FITS files"
)
parser.add_argument(
    "--file-prefix", '-f', type=str,
    default="fake_frame",
    help="Prefix of FITS files to monitor (e.g. 'fake_frame' to match 'fake_frame*.fits')"
)
parser.add_argument(
    "-c", "--rolling-cubes", type=int,
    default=5,
    help="Number of recent cubes to show in the rolling plot"
)
parser.add_argument(
    "--max-frames-global", "-g", type=int,
    default=100_000,
    help="Maximum number of frames to show in the global plot (older frames will be truncated)"
)



def parse_args(argv=None):
    return parser.parse_args(argv)