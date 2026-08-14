from __future__ import annotations

import argparse
import json

from certo_fdi.experiments.stage1_pipeline import run_full_pipeline


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    print(json.dumps(run_full_pipeline(args.config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
