import logging
import uuid
import inspect
import rasa
import json
import asyncio
from sanic import Blueprint, response
from sanic.request import Request
from socketio import AsyncServer
from typing import Text, List, Dict, Any, Optional, Callable, Iterable, Awaitable
from asyncio import Queue, CancelledError
from rasa.core.channels.channel import UserMessage, OutputChannel, CollectingOutputChannel, InputChannel
logger = logging.getLogger(__name__)

class ChatbotInput(InputChannel):
    
    @classmethod
    def name(cls):
        print("hi from name method")
        return "chatroom"

    @staticmethod
    async def on_message_wrapper(
        on_new_message: Callable[[UserMessage], Awaitable[None]],
        text: Text,
        queue: Queue,
        sender_id: Text,
    ) -> None:

        collector = Queue(queue)
        print('collector:',collector)

        message = UserMessage(
            text, collector, sender_id, input_channel=ChatbotInput.name()
        )
        print('message1: ',message.input_channel)

        await on_new_message(message)

        await queue.put("DONE") 

    async def _extract_sender(self, req) -> Optional[Text]:
        return req.json.get("sender", None)

    def _extract_metadata(self, req: Request) -> Text:
        return req.json.get("metadata") or self.name()

    def _extract_message(self, req):
        print("User message ::- ",req.json.get("message", None))
        return req.json.get("message", None)

    def _extract_input_channel(self, req: Request) -> Text:
        return req.json.get("input_channel") or self.name()

    def stream_response(
        self,
        on_new_message: Callable[[UserMessage], Awaitable[None]],
        text: Text,
        sender_id: Text,
    ) -> Callable[[Any], Awaitable[None]]:
        async def stream(resp: Any) -> None:
            q = Queue()
            task = asyncio.ensure_future(
                self.on_message_wrapper(on_new_message, text, q, sender_id)
            )
            while True:
                result = await q.get()
                if result == "DONE":
                    break
                else:
                    await resp.write(json.dumps(result) + "\n")
            await task

        return stream 

    def blueprint(self, on_new_message: Callable[[UserMessage], Awaitable[None]]):
        custom_webhook = Blueprint(
            "custom_webhook_{}".format(type(self).__name__),
            inspect.getmodule(self).__name__,
        )

        @custom_webhook.route("/", methods=["GET"])
        async def health(request: Request):
            print("Inside health")
            return response.json({"status": "ok"})

        @custom_webhook.route("/webhook", methods=["POST"])
        async def receive(request: Request):
            print("Inside receive")
            sender_id = await self._extract_sender(request)
            text = self._extract_message(request)
            print("sender_id is ::-",sender_id)
            print("text is ::-",text)
            should_use_stream = rasa.utils.endpoints.bool_arg(
                request, "stream", default=False
            )

            input_channel = self._extract_input_channel(request)
            print('input_channel: ',input_channel)

            metadata = self._extract_metadata(request)
            metadata = "{\"metadata\": \"" + str(metadata) + "\"}"
            metadata = json.loads(metadata)
            print('-metadata:', metadata)
            if should_use_stream:
                return response.stream(
                    self.stream_response(on_new_message, text, sender_id),
                     content_type="text/event-stream",
                )
            else:
                collector = CollectingOutputChannel()
                on_new_message(UserMessage(text, collector, sender_id))
                print("collector MSG::",collector)

                try:
                    await on_new_message(
                        UserMessage(
                            text, collector, sender_id, input_channel=input_channel, metadata=metadata
                        )
                    )
                except CancelledError:
                    logger.error(
                        "Message handling timed out for "
                        "user message '{}'.".format(text)
                    )
                except Exception:
                    logger.exception(
                        "An exception occured while handling "
                        "user message '{}'.".format(text)
                    )
                return response.json(collector.messages)
                
        return custom_webhook
