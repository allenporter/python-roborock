from roborock.local_api import RoborockLocalClient

from .. import CommandVacuumError, DeviceData, RoborockCommand, RoborockException
from ..exceptions import VacuumError
from ..protocol import MessageParser
from ..roborock_message import MessageRetry, RoborockMessage, RoborockMessageProtocol
from .roborock_client_v1 import COMMANDS_SECURED, RoborockClientV1


class RoborockLocalClientV1(RoborockLocalClient, RoborockClientV1):
    def __init__(self, device_data: DeviceData, queue_timeout: int = 4):
        RoborockLocalClient.__init__(self, device_data, queue_timeout)
        RoborockClientV1.__init__(self, device_data, self._logger, "abc")

    def build_roborock_message(
        self, method: RoborockCommand | str, params: list | dict | int | None = None
    ) -> RoborockMessage:
        secured = True if method in COMMANDS_SECURED else False
        request_id, timestamp, payload = self._get_payload(method, params, secured)
        self._logger.debug("Building message id %s for method %s", request_id, method)
        request_protocol = RoborockMessageProtocol.GENERAL_REQUEST
        message_retry: MessageRetry | None = None
        if method == RoborockCommand.RETRY_REQUEST and isinstance(params, dict):
            message_retry = MessageRetry(method=params["method"], retry_id=params["retry_id"])
        return RoborockMessage(
            timestamp=timestamp, protocol=request_protocol, payload=payload, message_retry=message_retry
        )

    async def _send_command(
        self,
        method: RoborockCommand | str,
        params: list | dict | int | None = None,
    ):
        roborock_message = self.build_roborock_message(method, params)
        return await self.send_message(roborock_message)

    async def send_message(self, roborock_message: RoborockMessage):
        await self.validate_connection()
        method = roborock_message.get_method()
        params = roborock_message.get_params()
        request_id: int | None
        if not method or not method.startswith("get"):
            request_id = roborock_message.seq
            response_protocol = request_id + 1
        else:
            request_id = roborock_message.get_request_id()
            response_protocol = RoborockMessageProtocol.GENERAL_REQUEST
        if request_id is None:
            raise RoborockException(f"Failed build message {roborock_message}")
        local_key = self.device_info.device.local_key
        msg = MessageParser.build(roborock_message, local_key=local_key)
        if method:
            self._logger.debug(f"id={request_id} Requesting method {method} with {params}")
        # Send the command to the Roborock device
        async_response = self._async_response(request_id, response_protocol)
        self._send_msg_raw(msg)
        diagnostic_key = method if method is not None else "unknown"
        try:
            response = await async_response
        except VacuumError as err:
            self._diagnostic_data[diagnostic_key] = {
                "params": roborock_message.get_params(),
                "error": err,
            }
            raise CommandVacuumError(method, err) from err
        self._diagnostic_data[diagnostic_key] = {
            "params": roborock_message.get_params(),
            "response": response,
        }
        if roborock_message.protocol == RoborockMessageProtocol.GENERAL_REQUEST:
            self._logger.debug(f"id={request_id} Response from method {roborock_message.get_method()}: {response}")
        if response == "retry":
            retry_id = roborock_message.get_retry_id()
            return self.send_command(
                RoborockCommand.RETRY_REQUEST, {"retry_id": retry_id, "retry_count": 8, "method": method}
            )
        return response
