from mappings import _single_map, pipe_delim, single_val


def convert_s3_url(data_values):
    """
    Replace the endpoint with your ecs endpoint, or an amazon s3 endpoint if using aws
    """
    url = single_val(data_values)
    if "str" not in str(type(url)):
        return None
    return url.replace("s3://", "https://your.ecs.endpoint.ca/")
