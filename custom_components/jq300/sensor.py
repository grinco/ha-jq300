"""
Integration of the JQ-300/200/100 indoor air quality meter.

For more details about this component, please refer to
https://github.com/Limych/ha-jq300
"""

#
#  Copyright (c) 2020, Andrey "Limych" Khrolenok <andrey@khrolenok.ru>
#  Creative Commons BY-NC-SA 4.0 International Public License
#  (see LICENSE.md or https://creativecommons.org/licenses/by-nc-sa/4.0/)
#

import logging

from homeassistant.components.sensor import ENTITY_ID_FORMAT
from homeassistant.const import CONF_USERNAME, CONF_DEVICE_ID
from homeassistant.helpers.entity import Entity, async_generate_entity_id

from . import JqController
from .const import DATA_JQ300, SENSORS, ATTR_DEVICE_ID, ATTR_DEVICE_BRAND, \
    ATTR_DEVICE_MODEL, ATTR_RAW_STATE

_LOGGER = logging.getLogger(__name__)


# pylint: disable=W0613
async def async_setup_platform(hass, config, async_add_entities,
                               discovery_info=None):
    """Set up a sensors to integrate JQ-300."""
    if discovery_info is None:
        return

    account_id = discovery_info[CONF_USERNAME]
    device_id = discovery_info[CONF_DEVICE_ID]
    _LOGGER.debug('Setup sensors for device %s', device_id)

    controller = hass.data[DATA_JQ300][account_id]  # type: JqController
    device = controller.get_devices_list()
    # _LOGGER.debug(device)
    if not device:
        _LOGGER.error("Can't receive devices list from cloud.")
        return
    device = device[device_id]
    dev_name = device['pt_name']
    sensors_data = controller.get_sensors(device_id)
    # _LOGGER.debug(sensors_data)
    if not sensors_data:
        _LOGGER.error("Can't receive sensors list for device '%s' from cloud.",
                      device['pt_name'])
        return

    sensors = []
    for sensor_id, sensor_state in sensors_data.items():
        if sensor_id not in SENSORS.keys():
            continue
        ent_name = SENSORS.get(sensor_id)[4] or SENSORS.get(sensor_id)[0]
        entity_id = async_generate_entity_id(
            ENTITY_ID_FORMAT, f"{dev_name}_{ent_name}", hass=hass)
        _LOGGER.debug("Initialize %s for account %s", entity_id, account_id)
        sensors.append(JqSensor(
            hass, controller, device, sensor_id, sensor_state, entity_id))

    async_add_entities(sensors)


# pylint: disable=R0902
class JqSensor(Entity):
    """A sensor implementation for JQ device"""

    # pylint: disable=R0913,W0613
    def __init__(self, hass, controller, device, sensor_id, sensor_state,
                 entity_id):
        """Initialize a sensor"""
        super().__init__()

        self._controller = controller  # type: JqController
        self._device_id = device['deviceid']
        self._device_brand = device['brandname']
        self._device_model = device['pt_model']
        self._sensor_id = sensor_id
        self._name = "{0} {1}".format(
            device['pt_name'], SENSORS.get(sensor_id)[0])
        self._state = sensor_state
        self._state_raw = sensor_state
        self._units = controller.units[sensor_id]
        self._icon = SENSORS.get(sensor_id)[2]
        self._unique_id = '{}-{}-{}'.format(
            self._controller.unique_id, self._device_id, sensor_id)
        self._device_class = SENSORS.get(sensor_id)[3]

        self.entity_id = entity_id

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._controller.available

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unique_id(self):
        """Return a unique ID."""
        return self._unique_id

    @property
    def device_class(self):
        """Return the class of the sensor."""
        return self._device_class

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {
            ATTR_DEVICE_BRAND: self._device_brand,
            ATTR_DEVICE_MODEL: self._device_model,
            ATTR_DEVICE_ID: self._device_id,
            ATTR_RAW_STATE: self._state_raw,
        }
        return attrs

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return self._icon

    @property
    def unit_of_measurement(self):
        """Return the units of measurement."""
        return self._units

    @property
    def should_poll(self):
        """Return the polling state."""
        return True

    def update(self):
        """Update the sensor state if it needed."""
        ret = self._controller.get_sensors(self._device_id)
        if ret:
            self._state = ret[self._sensor_id]
            self._state_raw = self._controller.get_sensors_raw(
                self._device_id)[self._sensor_id]
            _LOGGER.debug('Update state: %s = %s (%s)', self.entity_id,
                          self._state, self._state_raw)
