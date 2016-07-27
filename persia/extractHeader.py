def extract_txn_req_method(headers):
    ''' Extracts the HTTP request method from the header in a string format '''
    line = (headers.split('\r\n'))[0]
    return (line.split(' '))[0]

def extract_host(headers):
    ''' Returns the host header from the given headers '''
    lines = headers.split('\r\n')
    for line in lines:
        if 'Host:' in line:
            return line.split(' ')[1]
    return "notfound"


def header_to_dict(header):
    ''' Convert a HTTP header in string format to a python dictionary
    Returns a dictionary of header values
    '''
    header = header.split('\r\n')
    header = [x for x in header if (x != u'')]
    headers = {}
    for line in header:
        if 'GET' in line:     # ignore initial request line
            continue

        split_here = line.find(":")
        headers[line[:split_here]] = line[(split_here + 1):].strip()

    return headers        

def extract_GET_path(headers):
    ''' Extracts the HTTP request URL from the header in a string format '''
    line = (headers.split('\r\n'))[0]
    return (line.split(' '))[1]
