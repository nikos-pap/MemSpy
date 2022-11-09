from dataclasses import dataclass,field
from typing import List
from multiprocessing import Event
message_types:List[int] = ['EXIT', 'ADD_ADDRESS', 'DELETE_ADDRESS', 'EDIT_ADDRESS', 'FREEZE_ADDRESS', 'UNFREEZE_ADDRESS', 'RESET', 'EMPTY', 'ADDRESS_ADDED', 'ADDRESS_CHANGED']

@dataclass
class Message:
    message_type:str = 'EMPTY'
    message:List[int]= field(default_factory=list)


terminate = lambda e: Message('EXIT', [e])
add_address = lambda address: Message('ADD_ADDRESS', [address])
delete_address = lambda address: Message('DELETE_ADDRESS', [address])
edit_address = lambda address, value: Message('EDIT_ADDRESS', [address, value])
freeze_address = lambda address: Message('FREEZE_ADDRESS', [address])
unfreeze_address = lambda address: Message('UNFREEZE_ADDRESS', [address])
reset_process = lambda: Message('RESET')
empty = Message('EMPTY', [])

value_changed = lambda address: Message('ADDRESS_CHANGED', [address])
address_added = lambda success: Message('ADDRESS_ADDED', [success])