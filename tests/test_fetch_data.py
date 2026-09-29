import os
import sys
import zipfile
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from scripts import fetch_data

URL = 'https://github.com/example/repo'


def _archive(path, files):
    with zipfile.ZipFile(path, 'w') as bundle:
        for name, content in files.items():
            bundle.writestr('repo-abc123/' + name, content)


def _fake_download(files):
    def retrieve(_url, destination):
        _archive(destination, files)
    return retrieve


def test_a_zip_download_lands_without_its_top_folder(tmp_path):
    target = str(tmp_path / 'repo')
    files = {'data/one.csv': 'a,b', 'readme.md': 'hello'}
    with patch.object(fetch_data.urllib.request, 'urlretrieve', side_effect=_fake_download(files)):
        assert fetch_data._download_zip(URL, target)

    assert open(os.path.join(target, 'data', 'one.csv')).read() == 'a,b'
    assert open(os.path.join(target, 'readme.md')).read() == 'hello'
    assert not os.path.exists(target + '.zip')
    assert not os.path.exists(target + '.part')


def test_a_zip_with_a_path_leaving_the_folder_is_refused(tmp_path):
    target = str(tmp_path / 'repo')
    files = {'../escape.txt': 'no'}
    with patch.object(fetch_data.urllib.request, 'urlretrieve', side_effect=_fake_download(files)):
        assert not fetch_data._download_zip(URL, target)

    assert not os.path.exists(str(tmp_path / 'escape.txt'))
    assert not os.path.exists(target)


def test_a_failed_download_leaves_nothing_half_written(tmp_path):
    target = str(tmp_path / 'repo')
    with patch.object(fetch_data.urllib.request, 'urlretrieve', side_effect=OSError('offline')):
        assert not fetch_data._download_zip(URL, target)

    assert not os.path.exists(target)
    assert not os.path.exists(target + '.part')


def test_an_existing_folder_is_left_alone(tmp_path):
    target = tmp_path / 'repo'
    target.mkdir()
    (target / 'kept.txt').write_text('mine')
    with patch.object(fetch_data, '_clone') as clone, patch.object(fetch_data, '_download_zip') as zipped:
        assert fetch_data._obtain(URL, str(target), use_git=True)

    clone.assert_not_called()
    zipped.assert_not_called()


def test_git_is_used_when_asked_and_zip_otherwise(tmp_path):
    with patch.object(fetch_data, '_clone', return_value=True) as clone, \
         patch.object(fetch_data, '_download_zip', return_value=True) as zipped:
        fetch_data._obtain(URL, str(tmp_path / 'a'), use_git=True)
        fetch_data._obtain(URL, str(tmp_path / 'b'), use_git=False)

    assert clone.call_count == 1
    assert zipped.call_count == 1


def test_declining_the_licence_downloads_nothing():
    with patch('builtins.input', return_value='n'), \
         patch.object(fetch_data, '_obtain') as obtain:
        assert not fetch_data.fetch()

    obtain.assert_not_called()


def test_a_closed_input_counts_as_declining():
    with patch('builtins.input', side_effect=EOFError), \
         patch.object(fetch_data, '_obtain') as obtain:
        assert not fetch_data.fetch()

    obtain.assert_not_called()


def test_the_choice_of_git_follows_what_is_installed():
    with patch.object(fetch_data.shutil, 'which', return_value=None):
        assert not fetch_data._git_available()
    with patch.object(fetch_data.shutil, 'which', return_value='C:/git.exe'):
        assert fetch_data._git_available()
