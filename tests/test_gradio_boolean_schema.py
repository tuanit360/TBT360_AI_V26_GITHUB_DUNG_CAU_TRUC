"""Regression: boolean JSON Schemas must not crash the Gradio API type parser."""
import unittest
from app.gradio_compat import install_boolean_schema_support


class GradioBooleanSchemaTests(unittest.TestCase):
    def test_boolean_schema_and_nested_properties(self):
        import gradio_client.utils as utils
        install_boolean_schema_support()
        self.assertEqual(utils._json_schema_to_python_type(True, {}), 'Any')
        self.assertEqual(utils._json_schema_to_python_type(False, {}), 'Never')
        nested = {
            'type': 'object',
            'properties': {'flags': {'type': 'object', 'additionalProperties': True}},
        }
        self.assertIn('Any', utils.json_schema_to_python_type(nested))

    def test_install_twice_is_safe(self):
        import gradio_client.utils as utils
        install_boolean_schema_support()
        first = utils._json_schema_to_python_type
        install_boolean_schema_support()
        self.assertIs(first, utils._json_schema_to_python_type)
