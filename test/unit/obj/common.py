# Copyright (c) 2013 - 2015 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import hashlib
import os
import shutil
import tempfile
import unittest
import time

from swift.common.storage_policy import POLICIES
from swift.common.utils import Timestamp
from swift.obj import diskfile

from test.unit import debug_logger


class FakeReplicator(object):
    def __init__(self, testdir, policy=None):
        self.logger = debug_logger('test-ssync-sender')
        self.conn_timeout = 1
        self.node_timeout = 2
        self.http_timeout = 3
        self.network_chunk_size = 65536
        self.disk_chunk_size = 4096
        conf = {
            'devices': testdir,
            'mount_check': 'false',
        }
        policy = POLICIES.default if policy is None else policy
        self._diskfile_router = diskfile.DiskFileRouter(conf, self.logger)
        self._diskfile_mgr = self._diskfile_router[policy]


def write_diskfile(df, timestamp, data='test data', frag_index=None,
                   commit=True, extra_metadata=None):
    # Helper method to write some data and metadata to a diskfile.
    # Optionally do not commit the diskfile
    with df.create() as writer:
        writer.write(data)
        metadata = {
            'ETag': hashlib.md5(data).hexdigest(),
            'X-Timestamp': timestamp.internal,
            'Content-Length': str(len(data)),
        }
        if extra_metadata:
            metadata.update(extra_metadata)
        if frag_index is not None:
            metadata['X-Object-Sysmeta-Ec-Frag-Index'] = str(frag_index)
        writer.put(metadata)
        if commit:
            writer.commit(timestamp)
        # else: don't make it durable
    return metadata


class BaseTest(unittest.TestCase):
    def setUp(self):
        # daemon will be set in subclass setUp
        self.daemon = None
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_diskfile(self, device='dev', partition='9',
                       account='a', container='c', obj='o', body='test',
                       extra_metadata=None, policy=None,
                       frag_index=None, timestamp=None, df_mgr=None,
                       commit=True):
        policy = policy or POLICIES.legacy
        object_parts = account, container, obj
        timestamp = Timestamp(time.time()) if timestamp is None else timestamp
        if df_mgr is None:
            df_mgr = self.daemon._diskfile_router[policy]
        df = df_mgr.get_diskfile(
            device, partition, *object_parts, policy=policy,
            frag_index=frag_index)
        write_diskfile(df, timestamp, data=body, extra_metadata=extra_metadata,
                       commit=commit)

        if commit:
            # when we write and commit stub data, sanity check it's readable
            # and not quarantined because of any validation check
            with df.open():
                self.assertEqual(''.join(df.reader()), body)
            # sanity checks
            listing = os.listdir(df._datadir)
            self.assertTrue(listing)
            for filename in listing:
                self.assertTrue(filename.startswith(timestamp.internal))
        return df

    def _make_open_diskfile(self, device='dev', partition='9',
                            account='a', container='c', obj='o', body='test',
                            extra_metadata=None, policy=None,
                            frag_index=None, timestamp=None, df_mgr=None):
        df = self._make_diskfile(device, partition, account, container, obj,
                                 body, extra_metadata, policy, frag_index,
                                 timestamp, df_mgr)
        df.open()
        return df
