# ledzephyr

CLI tool to report Zephyr Scale → qTest migration metrics per Jira project/team.

## Install

```bash
git clone https://github.com/heymumford/ledzephyr.git
cd ledzephyr
poetry install
```

## Usage

```bash
# Check API connectivity
lz doctor

# Generate metrics
lz metrics -p PROJECT_KEY -w 7d -w 30d --format table
```

## Config

Required environment variables:
```bash
LEDZEPHYR_JIRA_URL=https://your-domain.atlassian.net
LEDZEPHYR_JIRA_USERNAME=your.email@company.com
LEDZEPHYR_JIRA_API_TOKEN=your_jira_api_token
```

## Development

```bash
poetry run pytest                    # Run tests
poetry run pre-commit run --all-files # Quality checks
```

## License

MIT