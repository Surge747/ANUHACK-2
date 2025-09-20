import importlib.util
import sys

def execute_widget_code(python_file_path: str, inputs: dict) -> any:
    """
    Dynamically loads a Python module from a file and executes its `run_widget` function.

    WARNING: This method is NOT secure for production. It does not provide true sandboxing.
    For a hackathon, it's a pragmatic solution. For a real product, use Docker containers
    or a dedicated sandboxing library like `pychroot`.
    """
    module_name = "dynamic_widget_module"

    # Clean up any old versions of the module
    if module_name in sys.modules:
        del sys.modules[module_name]

    try:
        spec = importlib.util.spec_from_file_location(name=module_name, location=python_file_path)
        if not spec or not spec.loader:
            raise ImportError(f"Cannot create module spec from {python_file_path}")

        widget_module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = widget_module

        spec.loader.exec_module(widget_module)

        if not hasattr(widget_module, 'run_widget'):
            raise AttributeError("Widget code is missing the required 'run_widget' function.")

        run_function = getattr(widget_module, 'run_widget')
        result = run_function(inputs)
        return result
    except Exception as e:
        print(f"Error executing widget code from {python_file_path}: {e}")
        # Re-raise the exception to be caught by the API endpoint
        raise
    finally:
        if module_name in sys.modules:
            del sys.modules[module_name]