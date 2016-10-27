import json
from hyper import HTTP20Connection
import hyper

hyper.tls._context = hyper.tls.init_context()
hyper.tls._context.check_hostname = False
hyper.tls._context.verify_mode = hyper.compat.ssl.CERT_NONE

conn = HTTP20Connection('localhost:443', secure=True)
conn.request('GET', '/')
resp = conn.get_response()

# process initial page with book ids
index_data = json.loads(resp.read().decode("utf8"))

responses = []
chunk_size = 100
sites={"www.example.com", "www.blabla.com", "www.whatever.com"}
request_ids = []
for site in sites:
    request_ids = []
    request_id = conn.request('GET', book_details_path)
    request_ids.append(request_id)
for req_id in request_ids:
        response = conn.get_response(req_id)
        body = json.loads(response.read().decode("utf-8"))
        responses.append(body)
'''
# split initial set of urls into chunks of 100 items
for i in range(0, len(index_data), chunk_size):
    request_ids = []

    # make requests
    for _id in index_data[i:i+chunk_size]:
        book_details_path = "/book?id={}".format(_id)
        request_id = conn.request('GET', book_details_path)
        request_ids.append(request_id)

    # get responses
    for req_id in request_ids:
        response = conn.get_response(req_id)
        body = json.loads(response.read().decode("utf-8"))
        responses.append(body)
'''
