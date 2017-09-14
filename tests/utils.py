import mock
import socket

class MockUtils(object):
    @classmethod
    def get_mock_name(cls, thing, attr=None):
        return ".".join([
            name for name in [
                thing.__module__,
                thing.__name__,
                attr
            ] if name
        ])

    # class PatchPropertyContext(object):
    #     """ Create a context where a class or instance's property is patched. """
    #     def __init__(self, class_=None, instance=None, property_=None, new_value=None):
    #         if instance:
    #             class_ = instance.__class__
    #         self.mocked_name = MockUtils.get_mock_name(class_, property_)
    #         self.mocked_value = new_value
    #         self.patch = None
    #
    #     def __enter__(self):
    #         self.patch = mock.patch(
    #             self.mocked_name,
    #             new_callable=mock.PropertyMock,
    #             return_value=self.mocked_value
    #         )
    #         return self.patch
    #
    #     def __exit__(self, exc_type, exc_value, exc_traceback):
    #         self.patch.__exit__(exc_type, exc_value, exc_traceback)

class ConnectionUtils(object):

    @classmethod
    def check_connection(cls):
        try:
            # see if we can resolve the host name -- tells us if there is
            # a DNS listening

            # connect to the host -- tells us if the host is actually
            # reachable
            socket.create_connection(('8.8.8.8', 80), 2)
            return True
        except:
            pass
