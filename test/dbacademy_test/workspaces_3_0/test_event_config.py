import unittest
from dbacademy.workspaces_3_0.event_config_class import EventConfig


class TestEventConfig(unittest.TestCase):

    def test_create_event_config(self):
        event_config = EventConfig(event_id=1234, max_participants=250, description="Fun time!")
        self.assertEqual(1234, event_config.event_id)
        self.assertEqual(250, event_config.max_participants)
        self.assertEqual("Fun time!", event_config.description)

    def test_create_event_config_event_id(self):
        from dbacademy_test.workspaces_3_0 import test_assertion_error

        event = EventConfig(event_id=0, max_participants=250, description="Fun time!")
        self.assertEqual(0, event.event_id)

        # noinspection PyTypeChecker
        test_assertion_error(self, """The parameter "event_id" must be an integral value, found <class 'str'>.""", lambda: EventConfig(event_id="1234", max_participants=250, description="Fun time!"))

    def test_create_event_config_participant_count(self):
        from dbacademy_test.workspaces_3_0 import test_assertion_error

        # noinspection PyTypeChecker
        test_assertion_error(self, """The parameter "max_participants" must be an integral value, found <class 'str'>.""", lambda: EventConfig(event_id=1234, max_participants="250", description="Fun time!"))
        # noinspection PyTypeChecker
        test_assertion_error(self, """The parameter "max_participants" must be an integral value, found <class 'NoneType'>.""", lambda: EventConfig(event_id=1234, max_participants=None, description="Fun time!"))
        test_assertion_error(self, """The parameter "max_participants" must be greater than zero, found "0".""", lambda: EventConfig(event_id=1234, max_participants=0, description="Fun time!"))

    def test_create_event_config_description(self):
        from dbacademy_test.workspaces_3_0 import test_assertion_error

        event_config = EventConfig(event_id=1234, max_participants=250, description=None)
        self.assertIsNone(event_config.description)

        event_config = EventConfig(event_id=1234, max_participants=250, description="")
        self.assertIsNone(event_config.description)

        # noinspection PyTypeChecker
        test_assertion_error(self, """The parameter "description" must be a string value or None, found <class 'int'>.""", lambda: EventConfig(event_id=1234, max_participants=250, description=0))
        # noinspection PyTypeChecker


if __name__ == '__main__':
    unittest.main()
