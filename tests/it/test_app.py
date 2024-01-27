import re
import zipfile
from pathlib import Path

import pytest
import respx
from httpx import Response
from typer.testing import CliRunner

from deltaver.__main__ import app


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def _mock_pypi(respx_mock: respx.router.MockRouter, tmp_path: Path) -> None:
    with zipfile.ZipFile('tests/fixtures/pypi_mock.zip', 'r') as zip_ref:
        zip_ref.extractall(tmp_path)
    for line in Path('tests/fixtures/requirements.txt').read_text().strip().splitlines():
        package_name = line.split('==')[0]
        respx_mock.get('https://pypi.org/pypi/{0}/json'.format(package_name)).mock(return_value=Response(
            200,
            text=Path(tmp_path / 'fixtures/{0}_pypi_response.json'.format(package_name)).read_text(),
        ))


@pytest.fixture()
def latest_requirements_file(tmp_path):
    path = (tmp_path / 'requirements.txt')
    path.write_text('httpx==0.26.0')
    return path


@pytest.mark.usefixtures('_mock_pypi')
@respx.mock(assert_all_mocked=False)
def test(runner: CliRunner) -> None:
    got = runner.invoke(app, ['tests/fixtures/requirements.txt'])

    assert got.exit_code == 0
    assert re.match(
        r'Scanning... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% \d:\d{2}:\d{2}',
        got.stdout.splitlines()[0],
    )
    assert got.stdout.splitlines()[1:] == [
        '┏━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━┓',
        '┃ Package      ┃ Version ┃ Delta (days) ┃',
        '┡━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━┩',
        '│ SQLAlchemy   │ 1.4.51  │ 366          │',
        '│ smmap        │ 5.0.1   │ 132          │',
        '│ jsonschema   │ 4.21.0  │ 8            │',
        '│ MarkupSafe   │ 2.1.3   │ 8            │',
        '│ diff_cover   │ 8.0.2   │ 7            │',
        '│ cryptography │ 41.0.7  │ 5            │',
        '│ bandit       │ 1.7.6   │ 4            │',
        '│ pluggy       │ 1.3.0   │ 3            │',
        '│ refurb       │ 1.27.0  │ 3            │',
        '└──────────────┴─────────┴──────────────┘',
        'Max delta: 366',
        'Average delta: 59.56',
    ]


@pytest.mark.usefixtures('_mock_pypi')
def test_zero_delta(latest_requirements_file, runner):
    got = runner.invoke(app, [str(latest_requirements_file)])

    assert got.exit_code == 0
    assert got.stdout.splitlines()[-2] == 'Max delta: 0'
    assert got.stdout.splitlines()[-1] == 'Average delta: 0'
