# SPDX-License-Identifier: Apache-2.0
#
# The OpenSearch Contributors require contributions made to
# this file be licensed under the Apache-2.0 license or a
# compatible open source license.

import os
import tempfile
import unittest
from unittest.mock import mock_open, patch

import yaml

from manifests.build_manifest import BuildManifest


class TestBuildManifest(unittest.TestCase):
    def setUp(self):
        self.data_path = os.path.realpath(os.path.join(os.path.dirname(__file__), "data"))
        self.manifest_filename = os.path.join(self.data_path, "opensearch-build-1.1.0.yml")
        self.manifest = BuildManifest.from_path(self.manifest_filename)

    def test_build(self):
        self.assertEqual(self.manifest.version, "1.2")
        self.assertEqual(self.manifest.build.name, "OpenSearch")
        self.assertEqual(self.manifest.build.version, "1.1.0")
        self.assertEqual(len(self.manifest.components), 15)

    def test_component(self):
        opensearch_component = self.manifest.components["OpenSearch"]
        self.assertEqual(opensearch_component.name, "OpenSearch")
        self.assertEqual(
            opensearch_component.repository,
            "https://github.com/opensearch-project/OpenSearch.git",
        )
        self.assertEqual(opensearch_component.commit_id, "b7334f49d530ffd1a3f7bd0e5832b9b2a9caa583")
        self.assertEqual(opensearch_component.ref, "1.x")
        self.assertEqual(
            sorted(opensearch_component.artifacts.keys()),
            ["core-plugins", "dist", "maven"],
        )

    def test_to_dict(self):
        data = self.manifest.to_dict()
        with open(self.manifest_filename) as f:
            self.assertEqual(yaml.safe_load(f), data)

    def test_get_manifest_relative_location(self):
        actual = BuildManifest.get_build_manifest_relative_location("25", "1.1.0", "linux", "x64")
        # TODO: use platform, https://github.com/opensearch-project/opensearch-build/issues/669
        expected = "builds/1.1.0/25/x64/manifest.yml"
        self.assertEqual(actual, expected, "the manifest relative location is not as expected")

    def test_components_index(self):
        component = self.manifest.components["index-management"]
        self.assertEqual(component.name, "index-management")

    def test_components_index_error(self):
        with self.assertRaises(KeyError) as ctx:
            self.manifest.components["invalid-component"]
        self.assertEqual(str(ctx.exception), "'invalid-component'")

    @patch("os.remove")
    @patch("builtins.open", mock_open())
    @patch("manifests.build_manifest.BuildManifest.from_path")
    @patch("manifests.build_manifest.S3Bucket")
    def test_from_s3(self, mock_s3_bucket, *mocks):
        s3_bucket = mock_s3_bucket.return_value
        s3_download_path = BuildManifest.get_build_manifest_relative_location(
            self.manifest.build.id,
            self.manifest.build.version,
            self.manifest.build.platform,
            self.manifest.build.architecture,
        )
        dest = os.path.realpath(os.path.join(tempfile.gettempdir(), "xyz"))
        BuildManifest.from_s3(
            "bucket_name",
            self.manifest.build.id,
            self.manifest.build.version,
            self.manifest.build.platform,
            self.manifest.build.architecture,
            dest,
        )
        self.assertEqual(s3_bucket.download_file.call_count, 1)
        s3_bucket.download_file.assert_called_with(s3_download_path, dest)
        os.remove.assert_called_with(os.path.join(dest, "manifest.yml"))

    def test_versions(self):
        self.assertTrue(len(BuildManifest.VERSIONS))
        for version in BuildManifest.VERSIONS:
            manifest = BuildManifest.from_path(os.path.join(self.data_path, "build", f"opensearch-build-schema-version-{version}.yml"))
            self.assertEqual(version, manifest.version)
            self.assertIsNotNone(any(manifest.components))

    def test_select(self):
        path = os.path.join(self.data_path, "build", "opensearch-build-schema-version-1.2.yml")
        manifest = BuildManifest.from_path(path)
        self.assertEqual(len(list(manifest.components.select(focus="common-utils"))), 1)

    def test_select_none(self):
        path = os.path.join(self.data_path, "build", "opensearch-build-schema-version-1.2.yml")
        manifest = BuildManifest.from_path(path)
        with self.assertRaises(ValueError) as ctx:
            self.assertEqual(len(list(manifest.components.select(focus="x"))), 0)
        self.assertEqual(str(ctx.exception), "No components matched focus=x.")

    def test_component_matches(self):
        self.assertTrue(BuildManifest.Component({"name": "x", "repository": "", "ref": "", "commit_id": "", "version": ""}).__matches__())

    def test_component_matches_focus(self):
        component = BuildManifest.Component({"name": "x", "repository": "", "ref": "", "commit_id": "", "version": ""})
        self.assertTrue(component.__matches__(focus=None))
        self.assertTrue(component.__matches__(focus="x"))
        self.assertFalse(component.__matches__(focus="y"))
