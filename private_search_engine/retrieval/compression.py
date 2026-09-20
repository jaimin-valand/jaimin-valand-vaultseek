from __future__ import annotations

def encode_varint(value: int) -> bytes:
    if value < 0: raise ValueError('value must be non-negative')
    out=bytearray()
    while value>=128: out.append((value&0x7F)|0x80); value>>=7
    out.append(value); return bytes(out)

def decode_varints(data: bytes) -> list[int]:
    values,value,shift=[],0,0
    for byte in data:
        value|=(byte&0x7F)<<shift
        if byte&0x80: shift+=7
        else: values.append(value); value=0; shift=0
    if shift: raise ValueError('truncated varint stream')
    return values

def encode_delta(ids: list[int]) -> bytes:
    ordered=sorted(ids); previous=0; out=bytearray()
    for item in ordered:
        if item<previous: raise ValueError('ids must be sortable')
        out+=encode_varint(item-previous); previous=item
    return bytes(out)

def decode_delta(data: bytes) -> list[int]:
    values=decode_varints(data); result=[]; previous=0
    for delta in values: previous+=delta; result.append(previous)
    return result
