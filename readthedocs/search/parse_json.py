"""Functions related to converting content into dict/JSON structures."""

import json
import logging

from django.conf import settings
from django.core.files.storage import get_storage_class

from pyquery import PyQuery


log = logging.getLogger(__name__)


def generate_sections_from_pyquery(body):
    """Given a pyquery object, generate section dicts for each section."""
    # Capture text inside h1 before the first h2
    h1_section = body('.section > h1')
    if h1_section:
        div = h1_section.parent()
        h1_title = h1_section.text().replace('¶', '').strip()
        h1_id = div.attr('id')
        h1_content = ''
        next_p = body('h1').next()
        while next_p:
            if next_p[0].tag == 'div' and 'class' in next_p[0].attrib:
                if 'section' in next_p[0].attrib['class']:
                    break

            h1_content += parse_content(next_p.text())
            next_p = next_p.next()
        if h1_content:
            yield {
                'id': h1_id,
                'title': h1_title,
                'content': h1_content.replace('\n', '. '),
            }

    # Capture text inside h2's
    section_list = body('.section > h2')
    for num in range(len(section_list)):
        div = section_list.eq(num).parent()
        header = section_list.eq(num)
        title = header.text().replace('¶', '').strip()
        section_id = div.attr('id')

        content = div.text()
        content = parse_content(content)

        yield {
            'id': section_id,
            'title': title,
            'content': content,
        }


def process_file(fjson_storage_path):
    """Read the fjson file from disk and parse it into a structured dict."""
    if not settings.RTD_BUILD_MEDIA_STORAGE:
        log.warning('RTD_BUILD_MEDIA_STORAGE is missing - Not updating intersphinx data')
        raise RuntimeError('RTD_BUILD_MEDIA_STORAGE is missing - Not updating intersphinx data')

    storage = get_storage_class(settings.RTD_BUILD_MEDIA_STORAGE)()

    log.debug('Processing JSON file for indexing: %s', fjson_storage_path)

    try:
        with storage.open(fjson_storage_path, mode='r') as f:
            file_contents = f.read()
    except IOError:
        log.info('Unable to read file: %s', fjson_storage_path)
        raise
    data = json.loads(file_contents)
    sections = []
    path = ''
    title = ''

    if 'current_page_name' in data:
        path = data['current_page_name']
    else:
        log.info('Unable to index file due to no name %s', fjson_storage_path)

    if data.get('body'):
        body = PyQuery(data['body'])
        sections.extend(generate_sections_from_pyquery(body))
    else:
        log.info('Unable to index content for: %s', fjson_storage_path)

    if 'title' in data:
        title = data['title']
        title = PyQuery(data['title']).text().replace('¶', '').strip()
    else:
        log.info('Unable to index title for: %s', fjson_storage_path)

    return {
        'path': path,
        'title': title,
        'sections': sections,
    }


def parse_content(content):
    """
    Removes the starting text and ¶.

    It removes the starting text from the content
    because it contains the title of that content,
    which is redundant here.
    """
    content = content.replace('¶', '').strip()

    # removing the starting text of each
    content = content.split('\n')
    if len(content) > 1:  # there were \n
        content = content[1:]

    # converting newlines to ". "
    content = '. '.join([text.strip().rstrip('.') for text in content])
    return content
