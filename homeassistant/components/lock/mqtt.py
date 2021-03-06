"""
Support for MQTT locks.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/lock.mqtt/
"""
import logging

import homeassistant.components.mqtt as mqtt
from homeassistant.components.lock import LockDevice
from homeassistant.const import CONF_VALUE_TEMPLATE
from homeassistant.helpers import template

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "MQTT Lock"
DEFAULT_PAYLOAD_LOCK = "LOCK"
DEFAULT_PAYLOAD_UNLOCK = "UNLOCK"
DEFAULT_QOS = 0
DEFAULT_OPTIMISTIC = False
DEFAULT_RETAIN = False

DEPENDENCIES = ['mqtt']


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices_callback, discovery_info=None):
    """Setup the MQTT lock."""
    if config.get('command_topic') is None:
        _LOGGER.error("Missing required variable: command_topic")
        return False

    add_devices_callback([MqttLock(
        hass,
        config.get('name', DEFAULT_NAME),
        config.get('state_topic'),
        config.get('command_topic'),
        config.get('qos', DEFAULT_QOS),
        config.get('retain', DEFAULT_RETAIN),
        config.get('payload_lock', DEFAULT_PAYLOAD_LOCK),
        config.get('payload_unlock', DEFAULT_PAYLOAD_UNLOCK),
        config.get('optimistic', DEFAULT_OPTIMISTIC),
        config.get(CONF_VALUE_TEMPLATE))])


# pylint: disable=too-many-arguments, too-many-instance-attributes
class MqttLock(LockDevice):
    """Represents a lock that can be toggled using MQTT."""
    def __init__(self, hass, name, state_topic, command_topic, qos, retain,
                 payload_lock, payload_unlock, optimistic, value_template):
        self._state = False
        self._hass = hass
        self._name = name
        self._state_topic = state_topic
        self._command_topic = command_topic
        self._qos = qos
        self._retain = retain
        self._payload_lock = payload_lock
        self._payload_unlock = payload_unlock
        self._optimistic = optimistic

        def message_received(topic, payload, qos):
            """A new MQTT message has been received."""
            if value_template is not None:
                payload = template.render_with_possible_json_value(
                    hass, value_template, payload)
            if payload == self._payload_lock:
                self._state = True
                self.update_ha_state()
            elif payload == self._payload_unlock:
                self._state = False
                self.update_ha_state()

        if self._state_topic is None:
            # Force into optimistic mode.
            self._optimistic = True
        else:
            mqtt.subscribe(hass, self._state_topic, message_received,
                           self._qos)

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def name(self):
        """The name of the lock."""
        return self._name

    @property
    def is_locked(self):
        """Return true if lock is locked."""
        return self._state

    @property
    def assumed_state(self):
        """Return true if we do optimistic updates."""
        return self._optimistic

    def lock(self, **kwargs):
        """Lock the device."""
        mqtt.publish(self.hass, self._command_topic, self._payload_lock,
                     self._qos, self._retain)
        if self._optimistic:
            # Optimistically assume that switch has changed state.
            self._state = True
            self.update_ha_state()

    def unlock(self, **kwargs):
        """Unlock the device."""
        mqtt.publish(self.hass, self._command_topic, self._payload_unlock,
                     self._qos, self._retain)
        if self._optimistic:
            # Optimistically assume that switch has changed state.
            self._state = False
            self.update_ha_state()
