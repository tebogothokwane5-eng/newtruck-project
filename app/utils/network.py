import threading
import requests


class NetworkClient:

    DEFAULT_TIMEOUT = 30

    # -------------------------
    # CORE REQUEST HANDLER
    # -------------------------
    @staticmethod
    def _request(method, url, *, json=None, data=None, files=None, headers=None, callback=None):
        def run():
            response = None
            error = None

            try:
                response = requests.request(
                    method=method,
                    url=url,
                    json=json,
                    data=data,
                    files=files,
                    headers=headers,
                    timeout=NetworkClient.DEFAULT_TIMEOUT
                )

                

            except Exception as e:
                error = e

            finally:
                # Close file handles safely
                if files:
                    for f in files.values():
                        try:
                            file_obj = f[1] if isinstance(f, tuple) else f
                            file_obj.close()
                        except Exception:
                            pass

            if callback:
                callback(response, error)

        threading.Thread(target=run, daemon=True).start()

    # -------------------------
    # HTTP METHODS
    # -------------------------

    @staticmethod
    def get(url, headers=None, callback=None):
        NetworkClient._request(
            "GET",
            url,
            headers=headers,
            callback=callback
        )

    @staticmethod
    def post(url, json=None, data=None, files=None, headers=None, callback=None):
        NetworkClient._request(
            "POST",
            url,
            json=json,
            data=data,
            files=files,
            headers=headers,
            callback=callback
        )

    @staticmethod
    def patch(url, json=None, data=None, headers=None, callback=None):
        NetworkClient._request(
            "PATCH",
            url,
            json=json,
            data=data,
            headers=headers,
            callback=callback
        )

    @staticmethod
    def delete(url, headers=None, callback=None):
        NetworkClient._request(
            "DELETE",
            url,
            headers=headers,
            callback=callback
        )