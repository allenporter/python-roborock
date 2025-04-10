# Async MQTT Design

## Usage

```python

# This will issues a basic API call, like getting user data, just whatever is
# needed to bootstrap everything else.
try:
    session: RoborockSession = await create_roborock_session(uid, auth_token)
except AuthException as err:
    raise RuntimeError(f"Authentication failed") from err
except ConnectException as err:
    raise RuntimeError(f"Could not connect") from err
    

# Account details were fetched. These don't really change so they're read on
# start and cached. (Not sure if this is true)
account_info = session.account_info()
print(account_info.email)

# Get devices. This can call the API to get the list of devices, and can start
# an MQTT session if it isn't started already. This will fetch initial state
# for each device and ensure each device is listening for updates from the
# MQTT session.
try:
    devices = await session.get_devices()
except ConnectException as err:
    raise RuntimeError(f"Could not retrieve devices") from err

# This is a client callback that can be notified when the device state changes
def notify() -> None:
    print("Device state has updated")
    for room_id, room_info in device.rooms.items():
        if room_id == device.current_room_id:
            print(f"{room_info.name} (current room)")
        else:
            print(room_info.name)

unsub = device.add_listener(my_notify)

# A device may have traits that have properties/commands
if device.map:
    img: PIL.Image = await device.map.get_map_image()

# Done listening to device. Close the MQTT session.
unsub()
await session.close()

```

## Internal APIs

```python

@dataclass
class MqttParams:
  mqqt_username: str
  mqtt_host: str
  ...

class MqttSession:
    def __init__(params: MqttParams) -> None:
        ...

    async def start() -> None:
        """Starts the mqtt loop"""

    async def close()
        """Cancels the mqtt loop"""

    async def subscribe(topic: str, callback: Callable[[bytes], None]) -> Callable[[], None]:
        """Invoke the callback when messages are received on the topic, returns unsub."""

    async def send_command(topic: str, message: bytes) -> MqttMessage:
        """Send a message."""


class DeviceSession:

    def __init__(device_info: DeviceInfo, session: MqttSession) -> None:
        self._device_info = device_info
        self._session = session
        self._unsub: Callable[[], None] = None
        
    async def start() -> None:
        self._unsub = await self._session.subscribe(
            self._device_info.mqtt_topic,
            self._receive
        )

    async def close() -> None:
        await _unsub()


    async def example_command() -> None:
        # Send a message. Blocks until the message is published
        payload = example_payload()
        message: MqttMessage = await self._session.send_command(
            self._device_info.mqtt_command_topic,
            payload,
        )
        # Block until the response is received.
        # TODO: Get into the weeds of message parsing
        async with asyncio.timeout(10):
            result = await message.wait_for_response()
            ...

....
