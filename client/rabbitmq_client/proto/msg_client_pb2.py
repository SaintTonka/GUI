# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: msg_client.proto
# Protobuf Python Version: 5.26.1
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x10msg_client.proto\x12\x11TestTask.Messages\"g\n\x07Request\x12\x16\n\x0ereturn_address\x18\x01 \x02(\t\x12\x12\n\nrequest_id\x18\x02 \x02(\t\x12\x1f\n\x17process_time_in_seconds\x18\x03 \x01(\x02\x12\x0f\n\x07request\x18\x04 \x02(\x05\"0\n\x08Response\x12\x12\n\nrequest_id\x18\x01 \x02(\t\x12\x10\n\x08response\x18\x02 \x02(\x05')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'msg_client_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_REQUEST']._serialized_start=39
  _globals['_REQUEST']._serialized_end=142
  _globals['_RESPONSE']._serialized_start=144
  _globals['_RESPONSE']._serialized_end=192
# @@protoc_insertion_point(module_scope)
