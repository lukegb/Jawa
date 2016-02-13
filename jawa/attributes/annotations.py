# -*- coding: utf8 -*-
from struct import unpack_from, pack
from jawa.attribute import Attribute


class ElementValue(object):

    def __init__(self, cf):
        self._cf = cf

    def unpack(self, info):
        self._tag, = unpack_from('>c', info)
        skip = 1

        if self._tag in b'BCDFIJSZs':
            self._value, = unpack_from('>H', info[skip:])
            skip += 2
        elif self._tag == b'e':
            self._value = unpack_from('>HH', info[skip:])
            skip += 4
        elif self._tag == b'c':
            self._value, = unpack_from('>H', info[skip:])
            skip += 2
        elif self._tag == b'@':
            annotation = RuntimeVisibleAnnotation(self._cf)
            skip += annotation.unpack(info[skip:])
            self._value = annotation
        elif self._tag == b'[':
            num_values, = unpack_from('>H', info[skip:])
            skip += 2
            values = []
            for n in range(num_values):
                value = ElementValue(self._cf)
                skip += value.unpack(info[skip:])
                values.append(value)
            self._value = values
        else:
            raise ValueError("Unknown ElementValue tag {}".format(self._tag))

        return skip

    @property
    def info(self):
        packed = pack('>c', self._tag)
        if self._tag in b'BCDFIJSZs':
            packed += pack('>H', self._value)
        elif self._tag == b'e':
            packed += pack('>HH', *self._value)
        elif self._tag == b'c':
            packed += pack('>H', self._value)
        elif self._tag == b'@':
            packed += self._value.info
        elif self._tag == b'[':
            packed += pack('>H', len(self._value))
            for value in self._values:
                packed += value.info
        return packed

    @property
    def value(self):
        if self._tag in b'BCDFIJSZs':
            return self._cf.constants.get(self._value)
        elif self._tag == b'e':
            type_name = self._cf.constants.get(self._value[0])
            const_name = self._cf.constants.get(self._value[1])
            return type_name, const_name
        elif self._tag == b'c':
            return self._cf.constants.get(self._value)
        elif self._tag == b'@':
            return self._value
        elif self._tag == b'[':
            return self._value
        else:
            raise ValueError("Unknown ElementValue tag {}".format(self._tag))


class RuntimeVisibleAnnotationsAttribute(Attribute):

    @classmethod
    def create(cls, cf, annotations):
        c = cls(cf, cf.constants.create_utf8('RuntimeVisibleAnnotations').index)
        c._num_annotations = len(annotations)
        c._annotations = annotations
        return c

    def unpack(self, info):
        num_annotations = unpack_from('>H', info)[0]
        info = info[2:]

        annotations = []
        for n in range(num_annotations):
            annotation = RuntimeVisibleAnnotation(self._cf)
            skip = annotation.unpack(info)
            info = info[skip:]
            annotations.append(annotation)

        self._annotations = annotations

    @property
    def info(self):
        packed = pack('>H', len(self._annotations))
        for annotation in self._annotations:
            packed += annotation.info
        return packed

    @property
    def annotations(self):
        return self._annotations


class RuntimeVisibleAnnotation(object):

    def __init__(self, cf):
        self._cf = cf

    def unpack(self, info):
        self._type_index, self._num_element_value_pairs = unpack_from('>HH', info)
        self._element_value_pairs = []
        skip = 4
        for n in range(self._num_element_value_pairs):
            element_name_index, = unpack_from('>H', info[skip:])
            skip += 2

            element_value = ElementValue(self._cf)
            skip += element_value.unpack(info[skip:])

            self._element_value_pairs.append((element_name_index, element_value))
        return skip

    @property
    def info(self):
        packed = pack('>HH', self._type_index, self._num_element_value_pairs)
        for name_index, value in self._element_value_pairs:
            packed += pack('>H', name_index)
            packed += value.info
        return packed

    @property
    def type(self):
        return self._cf.constants.get(self._type_index).value

    @property
    def key_value_pairs(self):
        for name_index, value in self._element_value_pairs:
            yield (self._cf.constants.get(name_index).value, value.value.value)
