import os


def get_str_var(var_name, default=None) -> str:
    """
    Get a string environment variable value or return a default value if not found.
    If no default value is specified or the default value is None this method
    will raise an exception.
    :param var_name: Name of the environment variable
    :param default: Default value to return if the environment variable is not found
    :return: The environment variable value or the default value
    """
    ret = os.getenv(var_name, default)
    if ret is None or ret == '':
        raise Exception("Environment variable '{}' not found.".format(var_name))
    return ret


def get_int_var(var_name, default=None) -> int:
    """
    Get an integer environment variable value or return a default value if not found
    If no default value is specified or the default value is None this method
    will raise an exception.
    :param var_name: Name of the environment variable
    :param default: Default value to return if the environment variable is not found
    :return: The environment variable value or the default value
    """
    return int(get_str_var(var_name, default))


def get_float_var(var_name, default=None) -> float:
    """
    Get a float environment variable value or return a default value if not found
    If no default value is specified or the default value is None this method
    will raise an exception.
    :param var_name: Name of the environment variable
    :param default: Default value to return if the environment variable is not found
    :return: The environment variable value or the default value
    """
    return float(get_str_var(var_name, default))


def get_bool_var(var_name, default=None) -> bool:
    """
    Get a boolean environment variable value or return a default value if not found
    If no default value is specified or the default value is None this method
    will raise an exception.
    :param var_name: Name of the environment variable
    :param default: Default value to return if the environment variable is not found
    :return: The environment variable value or the default value
    """
    return get_str_var(var_name, default).lower() in ['true', '1', 't', 'y', 'yes']
