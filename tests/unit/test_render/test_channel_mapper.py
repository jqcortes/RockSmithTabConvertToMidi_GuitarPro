"""tests for Render channel mapping."""

from __future__ import annotations


class TestChannelMapper:
    def test_assign_uses_fixed_channels_for_supported_roles(self) -> None:
        from pipeline.render.channel_mapper import ChannelMapper, RenderPartInfo

        parts = [
            RenderPartInfo(part_id="P1", part_name="Lead Guitar", role="guitar"),
            RenderPartInfo(part_id="P2", part_name="Bass", role="bass"),
            RenderPartInfo(part_id="P3", part_name="Drums", role="drums"),
        ]

        assignments = ChannelMapper.assign(parts)

        assert [assignment.part_id for assignment in assignments] == ["P1", "P2", "P3"]
        assert [(assignment.midi_channel, assignment.midi_program) for assignment in assignments] == [
            (1, 29),
            (2, 33),
            (10, None),
        ]

    def test_assign_allocates_other_parts_to_first_available_channels(self) -> None:
        from pipeline.render.channel_mapper import ChannelMapper, RenderPartInfo

        parts = [
            RenderPartInfo(part_id="P1", part_name="Lead Guitar", role="guitar"),
            RenderPartInfo(part_id="P2", part_name="Keys", role="other"),
            RenderPartInfo(part_id="P3", part_name="Strings", role="other"),
            RenderPartInfo(part_id="P4", part_name="Perc", role="other"),
        ]

        assignments = ChannelMapper.assign(parts)

        assert [(assignment.part_id, assignment.midi_channel, assignment.midi_program) for assignment in assignments] == [
            ("P1", 1, 29),
            ("P2", 3, 1),
            ("P3", 4, 1),
            ("P4", 5, 1),
        ]

    def test_assign_skips_reserved_drum_channel_for_other_parts(self) -> None:
        from pipeline.render.channel_mapper import ChannelMapper, RenderPartInfo

        parts = [
            RenderPartInfo(part_id=f"P{index}", part_name=f"Other {index}", role="other")
            for index in range(1, 10)
        ]

        assignments = ChannelMapper.assign(parts)

        assert [assignment.midi_channel for assignment in assignments] == [3, 4, 5, 6, 7, 8, 9, 11, 12]

        parts.append(RenderPartInfo(part_id="P10", part_name="Other 10", role="other"))
        assignments = ChannelMapper.assign(parts)

        assert [assignment.midi_channel for assignment in assignments][-1] == 13

    def test_assign_raises_when_no_channels_remain(self) -> None:
        import pytest

        from pipeline.render.channel_mapper import ChannelMapper, RenderPartInfo
        from pipeline.render.errors import RenderExecutionError

        parts = [
            RenderPartInfo(part_id=f"P{index}", part_name=f"Other {index}", role="other")
            for index in range(1, 17)
        ]

        with pytest.raises(RenderExecutionError, match="No MIDI channels available"):
            ChannelMapper.assign(parts)

    def test_to_metrics_map_serializes_assignment_summary(self) -> None:
        from pipeline.render.channel_mapper import ChannelAssignment, ChannelMapper

        assignments = [
            ChannelAssignment(part_id="P1", role="guitar", midi_channel=1, midi_program=29),
            ChannelAssignment(part_id="P2", role="drums", midi_channel=10, midi_program=None),
        ]

        assert ChannelMapper.to_metrics_map(assignments) == {
            "P1": "channel=1,program=29,role=guitar",
            "P2": "channel=10,program=none,role=drums",
        }