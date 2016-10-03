from typing import Tuple
import unittest
import threading
import functools
import contextlib
import json
import shutil
import io
import base64
from os import makedirs, urandom
from os.path import join, dirname, abspath, exists, split
from http.server import HTTPServer, BaseHTTPRequestHandler, HTTPStatus

from sqlalchemy import Unicode, TypeDecorator, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy_media import StoreManager, FileSystemStore
from sqlalchemy_media.typing import Stream
from sqlalchemy_media.helpers import copy_stream
from sqlalchemy_media.mimetypes_ import guess_type


Address = Tuple[str, int]


@contextlib.contextmanager
def simple_http_server(content: bytes= b'Simple file content.', bind: Address=('', 0), content_type: str=None):

    class SimpleHandler(BaseHTTPRequestHandler):

        def serve_text(self):
            self.send_header('Content-Type', "text/plain")
            self.send_header('Content-Length', str(len(content)))
            self.send_header('Last-Modified', self.date_time_string())
            self.end_headers()
            self.wfile.write(content)

        def serve_static_file(self, filename: str):
            self.send_header('Content-Type', guess_type(filename))
            with open(filename, 'rb') as f:
                self.serve_stream(f)

        def serve_stream(self, stream: Stream):
            buffer = io.BytesIO()
            self.send_header('Content-Length', str(copy_stream(stream, buffer)))
            self.end_headers()
            buffer.seek(0)
            copy_stream(buffer, self.wfile)

        def do_GET(self):
            self.send_response(HTTPStatus.OK)
            if isinstance(content, bytes):
                self.serve_text()
            elif isinstance(content, str):
                self.serve_static_file(content)
            else:
                self.send_header('Content-Type', content_type)
                self.serve_stream(content)

    http_server = HTTPServer(bind, SimpleHandler)
    thread = threading.Thread(target=http_server.serve_forever, name='sa-media test server.', daemon=True)
    thread.start()
    yield http_server
    http_server.shutdown()
    thread.join()


# noinspection PyAbstractClass
class Json(TypeDecorator):
    impl = Unicode

    def process_bind_param(self, value, engine):
        return json.dumps(value)

    def process_result_value(self, value, engine):
        if value is None:
            return None

        return json.loads(value)


class SqlAlchemyTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db_uri = 'sqlite:///:memory:'

    def setUp(self):
        self.Base = declarative_base()
        self.engine = create_engine(self.db_uri, echo=False)

    def create_all_and_get_session(self):
        self.Base.metadata.create_all(self.engine, checkfirst=True)
        self.session_factory = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=True,
            twophase=False
        )
        return self.session_factory()


class TempStoreTestCase(SqlAlchemyTestCase):

    @classmethod
    def setUpClass(cls):
        cls.this_dir = abspath(dirname(__file__))
        cls.stuff_path = join(cls.this_dir, 'stuff')
        super().setUpClass()

    def setUp(self):
        self.temp_path = join(self.this_dir, 'temp', self.__class__.__name__, self._testMethodName)
        self.base_url = 'http://static1.example.orm'

        # Remove previous files, if any! to make a clean temp directory:
        if exists(self.temp_path):
            shutil.rmtree(self.temp_path)

        makedirs(self.temp_path)

        StoreManager.register('fs', functools.partial(FileSystemStore, self.temp_path, self.base_url), default=True)
        super().setUp()


def encode_multipart_data(fields: dict=None, files: dict=None):
    BOUNDARY = ''.join(['-----', base64.urlsafe_b64encode(urandom(27)).decode()])
    CRLF = b'\r\n'
    lines = []

    if fields:
        for key, value in fields.items():
            lines.append('--' + BOUNDARY)
            lines.append('Content-Disposition: form-data; name="%s"' % key)
            lines.append('')
            lines.append(value)

    if files:
        for key, filepath in files.items():
            filename = split(filepath)[1]
            lines.append('--' + BOUNDARY)
            lines.append(
                'Content-Disposition: form-data; name="%s"; filename="%s"' %
                (key, filename))
            lines.append(
                'Content-Type: %s' %
                (guess_type(filename) or 'application/octet-stream'))
            lines.append('')
            lines.append(open(filepath, 'rb').read())

    lines.append('--' + BOUNDARY + '--')
    lines.append('')

    body = io.BytesIO()
    length = 0
    for l in lines:
        line = (l if isinstance(l, bytes) else l.encode()) + CRLF
        length += len(line)
        body.write(line)
    body.seek(0)
    content_type = 'multipart/form-data; boundary=%s' % BOUNDARY
    return content_type, body, length


if __name__ == '__main__':
    ct, b, l = encode_multipart_data(dict(test1='TEST1VALUE'), files=dict(cat='stuff/cat.jpg'))
    print(ct)
    print(l)
    print(b.read())

#    with simple_http_server(bind=('', 8080), content=b'simple text') as httpd:
#     with simple_http_server(bind=('', 8080), content='stuff/cat.jpg') as httpd:
#         target_url = 'http://%s:%s' % httpd.server_address
#         print(target_url)
#         time.sleep(1000)