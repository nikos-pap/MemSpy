from dataclasses import dataclass, field
from typing import List, Callable
from utils.address import Address

message_types: List[str] = ['EXIT', 'ADD_ADDRESS', 'DELETE_ADDRESS', 'EDIT_ADDRESS', 'FREEZE_ADDRESS',
                            'UNFREEZE_ADDRESS', 'RESET', 'EMPTY', 'ADDRESS_ADDED', 'ADDRESS_CHANGED']


@dataclass
class Message:
    message_type: str = 'EMPTY'
    message: List = field(default_factory=list)


terminate: Callable[[int], Message] = lambda e: Message('EXIT', [e])
add_address: Callable[[Address], Message] = lambda address: Message('ADD_ADDRESS', [address])
delete_address: Callable[[int], Message] = lambda address: Message('DELETE_ADDRESS', [address])
edit_address: Callable[[int], Message] = lambda address, value: Message('EDIT_ADDRESS', [address, value])
freeze_address: Callable[[int], Message] = lambda address: Message('FREEZE_ADDRESS', [address])
unfreeze_address: Callable[[int], Message] = lambda address: Message('UNFREEZE_ADDRESS', [address])
reset_process: Callable[[str], Message] = lambda m: Message('RESET', [m])
empty: Message = Message('EMPTY', [])
value_changed: Callable[[bool], Message] = lambda address: Message('ADDRESS_CHANGED', [address])
address_added: Callable[[bool], Message] = lambda success: Message('ADDRESS_ADDED', [success])
