import mido
mid = mido.MidiFile(".cache/manual-check/crash_complexion.mid")
print("type:", mid.type)
print("ticks_per_beat:", mid.ticks_per_beat)
print("tracks:", len(mid.tracks))
note_count = 0
for i, track in enumerate(mid.tracks):
    notes = [m for m in track if m.type == "note_on" and m.velocity > 0]
    note_count += len(notes)
    print(f"  Track {i} '{track.name}': {len(track)} msgs, {len(notes)} note_ons")
print("total notes:", note_count)
print("length:", round(mid.length, 1), "s")

