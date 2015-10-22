#!/usr/bin/env python3

import sys
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib

# http://docs.gstreamer.com/display/GstSDK/Basic+tutorial+6%3A+Media+formats+and+Pad+Capabilities

# the functions below print the capabilities in a human-friendly format


def print_field(field, value, pfx):
    str = Gst.value_serialize(value)
    print("{0:s}  {1:15s}: {2:s}".format(
        pfx, GLib.quark_to_string(field), str))
    return True


def print_caps(caps, pfx):
    if not caps:
        return

    if caps.is_any():
        print("{0:s}ANY".format(pfx))
        return

    if caps.is_empty():
        print("{0:s}EMPTY".format(pfx))
        return

    for i in range(caps.get_size()):
        structure = caps.get_structure(i)
        print("{0:s}{1:s}".format(pfx, structure.get_name()))
        structure.foreach(print_field, pfx)

# prints information about a pad template (including its capabilities)


def print_pad_templates_information(factory):
    print("Pad templates for {0:s}".format(factory.get_name()))
    if factory.get_num_pad_templates() == 0:
        print("  none")
        return

    pads = factory.get_static_pad_templates()
    for pad in pads:
        padtemplate = pad.get()

        if pad.direction == Gst.PadDirection.SRC:
            print("  SRC template:", padtemplate.name_template)
        elif pad.direction == Gst.PadDirection.SINK:
            print("  SINK template:", padtemplate.name_template)
        else:
            print("  UNKNOWN template:", padtemplate.name_template)

        if padtemplate.presence == Gst.PadPresence.ALWAYS:
            print("    Availability: Always")
        elif padtemplate.presence == Gst.PadPresence.SOMETIMES:
            print("    Availability: Sometimes")
        elif padtemplate.presence == Gst.PadPresence.REQUEST:
            print("    Availability: On request")
        else:
            print("    Availability: UNKNOWN")

        if padtemplate.get_caps():
            print("    Capabilities:")
            print_caps(padtemplate.get_caps(), "      ")

        print("")

# shows the current capabilities of the requested pad in the given element


def print_pad_capabilities(element, pad_name):
    # retrieve pad
    pad = element.get_static_pad(pad_name)
    if not pad:
        print("ERROR: Could not retrieve pad '{0:s}'".format(pad_name))
        return

    # retrieve negotiated caps (or acceptable caps if negotiation is not
    # yet finished)
    caps = pad.get_current_caps()
    if not caps:
        caps = pad.get_allowed_caps()

    # print
    print("Caps for the {0:s} pad:".format(pad_name))
    print_caps(caps, "      ")


def main():
    # initialize GStreamer
    Gst.init(sys.argv)

    # create the element factories
    source_factory = Gst.ElementFactory.find("audiotestsrc")
    sink_factory = Gst.ElementFactory.find("autoaudiosink")
    if not source_factory or not sink_factory:
        print("ERROR: Not all element factories could be created")
        return -1

    # print information about the pad templates of these factories
    print_pad_templates_information(source_factory)
    print_pad_templates_information(sink_factory)

    # ask the factories to instantiate the actual elements
    source = source_factory.create("source")
    sink = sink_factory.create("sink")

    # create the empty pipeline
    pipeline = Gst.Pipeline.new("test-pipeline")
    if not pipeline or not source or not sink:
        print("ERROR: Not all elements could be created")
        return -1

    # build the pipeline
    pipeline.add(source, sink)
    if not source.link(sink):
        print("ERROR: Could not link source to sink")
        return -1

    # print initial negotiated caps (in NULL state)
    print("In NULL state:")
    print_pad_capabilities(sink, "sink")

    # start playing
    ret = pipeline.set_state(Gst.State.PLAYING)
    if ret == Gst.StateChangeReturn.FAILURE:
        print("ERROR: Unable to set the pipeline to the playing state")

    # wait until error, EOS or State-Change
    terminate = False
    bus = pipeline.get_bus()
    while True:
        try:
            msg = bus.timed_pop_filtered(
                0.5 * Gst.SECOND,
                Gst.MessageType.ERROR | Gst.MessageType.EOS | Gst.MessageType.STATE_CHANGED)

            if msg:
                t = msg.type
                if t == Gst.MessageType.ERROR:
                    err, dbg = msg.parse_error()
                    print("ERROR:", msg.src.get_name(), ":", err.message)
                    if dbg:
                        print("Debug information:", dbg)
                    terminate = True
                elif t == Gst.MessageType.EOS:
                    print("End-Of-Stream reached")
                    terminate = True
                elif t == Gst.MessageType.STATE_CHANGED:
                    # we are only interested in state-changed messages from the
                    # pieline
                    if msg.src == pipeline:
                        old, new, pending = msg.parse_state_changed()
                        print(
                            "Pipeline state changed from",
                            Gst.Element.state_get_name(old),
                            "to",
                            Gst.Element.state_get_name(new),
                            ":")

                        # print the current capabilities of the sink
                        print_pad_capabilities(sink, "sink")
                else:
                    # should not get here
                    print("ERROR: unexpected message received")
        except KeyboardInterrupt:
            terminate = True

        if terminate:
            break

    pipeline.set_state(Gst.State.NULL)

if __name__ == '__main__':
    main()
