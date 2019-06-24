class TransifexException(Exception):
    pass


class PyTransifexException(TransifexException):
    def __init__(self, response=None):
        super(PyTransifexException, self).__init__(response)
        self.response = response

    def __str__(self):
        if self.response is None:
            return super(PyTransifexException, self).__str__()
        return '{code} from {url}: {content}'.format(
            code=self.response.status_code,
            url=self.response.url,
            content=self.response.content
        )


class InvalidSlugException(TransifexException):
    pass
