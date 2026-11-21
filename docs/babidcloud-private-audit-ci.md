# Babid C Cloud synthetic CI bridge (public Analytics → private Babid)

This repository is PUBLIC. The original Babid trading bot is PRIVATE.
Do **not** copy the Babid source, trade logs, account identifiers, risk snapshots,
instruments or credentials into Analytics or upload them as workflow artifacts.

The workflow `.github/workflows/babidcloud-private-audit.yml` can check out
the private repository at `chatgpt/babidcloud-audit-20261121` and run
`python -m unittest discover -p 'test_*.py' -v` under `BabidCCloud/analysis`
on Linux/Python 3.11 and Windows/Python 3.13.

**Required one-time action:** set an Analytics GitHub Actions repository secret
named `BABIDCLOUD_READ_TOKEN`. Use a fine-grained GitHub token limited to
**IskanderAbdullin/Babid-C-gpt-** with **Contents: Read-only**, and a short
expiration. Never paste the token into ChatGPT, an issue, file or workflow
input. Without this secret, the `access-check` job succeeds with an explicit
**NOT TESTED** warning, while both private test jobs are skipped. This is not
evidence of a successful audit.

The workflow uses `persist-credentials: false` for the private checkout;
it runs synthetic tests only and uploads no files. It does not attempt to
build/run the robot, retrieve trading data, connect to T-Invest or use the
user's Windows machine. Source commit SHA is printed for reproducibility.

A user-approved private token is required because the default
`GITHUB_TOKEN` from Analytics cannot read another private repository.
On pull requests from forks GitHub normally withholds secrets.

The branch trigger exists for initial verification of this CI design.
`workflow_dispatch` also allows manual runs once the workflow is on the
default branch. Any future addition of private integration tests must avoid
printing transaction data or publishing artifact archives.
