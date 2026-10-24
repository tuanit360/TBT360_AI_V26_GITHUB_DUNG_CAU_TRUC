"""Compatibility shim for Gradio 5.9.1 / gradio_client JSON Schema booleans.

JSON Schema permits a boolean schema (for example additionalProperties: true).
The bundled gradio_client parser assumes every schema is a dict. This prevents
Gradio's local API endpoint from responding and can surface as a misleading
'localhost not accessible' startup error. Keep this shim scoped to that case.
"""


def install_boolean_schema_support():
    import gradio_client.utils as client_utils

    original = client_utils._json_schema_to_python_type
    if getattr(original, '_tbt360_boolean_schema_support', False):
        return

    def convert(schema, defs):
        if schema is True:
            return 'Any'
        if schema is False:
            return 'Never'
        return original(schema, defs)

    convert._tbt360_boolean_schema_support = True
    client_utils._json_schema_to_python_type = convert
