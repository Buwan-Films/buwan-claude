/*  Buwan Films — Premiere Pro apply library (ExtendScript, ES3)
 *
 *  Runs inside Premiere through the MCP bridge (execute_extendscript) and applies what the
 *  assemble engine decided, from edit/premiere/manifest.json (assemble.js premiere <project>).
 *
 *  Load + run (one execute_extendscript call, ES3, raise timeout_ms for big steps):
 *      $.evalFile("<buwan-premiere plugin>/jsx/buwan.jsx");
 *      return __result(BUWAN.run("organize", "<project>/edit/premiere/manifest.json", "{limit:200}"));
 *
 *  Steps (the basics, in house order):
 *      status    what is in the project vs the manifest (new clips from shooters, missing ones)
 *      import    import manifest clips that are not in the project yet, straight into their bins
 *      organize  bins per category + Premiere label colors (rejects -> 00 Rejected (cull), Brown;
 *                shaky / soft / dark / frozen b-roll -> 00 Flagged/<reason>, category label kept)
 *      cull      only the rejects, with reasons
 *      grade     Lumetri Color + studio LUT on every camera clip of a sequence (opts.sequence or active)
 *      enhance   speech clips of a sequence: measured gain, DeNoise, Hard Limiter
 *      deadair   subclips of the speech ranges (dead air removed), bin "01 Speech/Speech ranges"
 *      aroll     the A-Roll clean sequence: every speech range back to back
 *      sync      one stacked SYNC sequence per multicam group, clips at their audio-sync offsets
 *      relink    point clips and their subclips at the BY_CATEGORY clones (batches: {limit}); trimmed best cuts stay on RAW_COPY
 *      steady    shaky Creative/Glider clips: best cut first (subclips in <category>/Steady picks); only gimbal shots with no steady stretch get Warp Stabilizer, on their best cut, in a STABILIZE sequence
 *      skeleton  (optional) an empty assembly sequence with section markers — only when asked
 *      build     the music-driven timeline from the plan (speech V1/A1, b-roll V2, music A3/A4, markers)
 *      basics    import, organize (bins, labels, rejects, flagged), deadair, aroll, steady, relink (BY_CATEGORY), grade (look + exposure on
 *                A-Roll clean and STABILIZE) — and stops. The same-day scope.
 *      all       import, organize, deadair, aroll, sync, build (if plan), grade, enhance
 *
 *  Nothing here deletes, renames or re-encodes footage. Everything is additive and undoable.
 */

var BUWAN = (function () {
  var TICKS = 254016000000;            // ticks per second
  var FRAME_TICKS = 10594584000;       // one frame at 23.976 (254016000000 * 1001 / 24000)
  var MAX_LOG = 400;
  var M = null;                        // manifest
  var index = null;                    // normalized media path -> {item, parent}
  var binCache = null;                 // "A/B" -> bin item
  var logs = [];

  // ---------- small helpers ----------
  function log(s) { if (logs.length < MAX_LOG) logs.push(String(s)); try { $.writeln("[buwan] " + s); } catch (e) {} }
  function has(arr, v) { for (var i = 0; i < arr.length; i++) if (arr[i] === v) return true; return false; }
  function trim(s) { return String(s).replace(/^\s+|\s+$/g, ""); }
  function norm(p) {
    if (!p) return "";
    var s = String(p).replace(/\\/g, "/");
    if (s.indexOf("file://") === 0) s = File.decode(s.substring(7));
    return s.toLowerCase();
  }
  function basename(p) { var s = String(p).replace(/\\/g, "/"); return s.substring(s.lastIndexOf("/") + 1); }
  function ticks(sec) { return String(Math.round(sec * TICKS)); }
  function ticksFrame(sec) { return String(Math.round(sec * 24000 / 1001) * FRAME_TICKS); }
  function dB(db) { return Math.pow(10, (db - 15) / 20); }   // Premiere Volume.Level: 1.0 = +15 dB, 0.1778 = 0 dB
  function fmt(sec) {
    var m = Math.floor(sec / 60), s = Math.floor(sec - m * 60);
    return (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
  }
  function readFile(path) {
    var f = new File(path);
    if (!f.exists) throw new Error("file not found: " + path);
    f.encoding = "UTF-8";
    if (!f.open("r")) throw new Error("cannot open: " + path);
    var t = f.read();
    f.close();
    return t;
  }
  function loadManifest(path) {
    var txt = readFile(path);
    M = eval("(" + txt + ")");
    if (!M || !M.clips) throw new Error("not a Buwan manifest: " + path);
    M._path = path;
    alias = null;
    return M;
  }
  function parseOpts(o) {
    if (!o) return {};
    if (typeof o === "string") { try { return eval("(" + o + ")") || {}; } catch (e) { throw new Error("opts must be an object literal: " + o); } }
    return o;
  }

  // ---------- project index ----------
  function walk(bin, parent, fn) {
    for (var i = 0; i < bin.children.numItems; i++) {
      var it = bin.children[i];
      fn(it, bin);
      if (it.type === 2) walk(it, bin, fn);
    }
  }
  var alias = null;
  function aliasOf() {                 // norm(BY_CATEGORY file) -> norm(RAW_COPY path), from the manifest
    if (alias) return alias;
    alias = {};
    if (M && M.clips) for (var i = 0; i < M.clips.length; i++) if (M.clips[i].category_file) alias[norm(M.clips[i].category_file)] = norm(M.clips[i].path);
    return alias;
  }
  function reindex() {
    index = {}; binCache = {};
    var root = app.project.rootItem;
    walk(root, null, function (it, parent) {
      if (it.type === 2) return;
      var mp = "";
      try { if (!it.isSequence()) mp = it.getMediaPath(); } catch (e) {}
      if (mp) {
        var k = norm(mp), viaAlias = !!aliasOf()[k];
        if (viaAlias) k = aliasOf()[k];   // relinked to BY_CATEGORY: still found by its RAW_COPY path
        // the imported master (named like the file it was imported from) wins over subclips that share the path
        var isMaster = String(it.name).toLowerCase() === basename(viaAlias ? k : mp).toLowerCase();
        if (!index[k] || (isMaster && !index[k].master)) index[k] = { item: it, parent: parent, master: isMaster };
      }
    });
    return index;
  }
  function itemFor(path) {
    if (!index) reindex();
    var e = index[norm(path)];
    return e ? e.item : null;
  }
  function parentOf(path) {
    if (!index) reindex();
    var e = index[norm(path)];
    return e ? e.parent : null;
  }
  function childBin(parent, name) {
    for (var i = 0; i < parent.children.numItems; i++) {
      var it = parent.children[i];
      if (it.type === 2 && it.name === name) return it;
    }
    return null;
  }
  function bin(pathName) {           // "01 Speech" or "01 Speech/Speech ranges"; created when missing
    if (!binCache) binCache = {};
    if (binCache[pathName]) return binCache[pathName];
    var parts = String(pathName).split("/"), cur = app.project.rootItem, acc = "";
    for (var i = 0; i < parts.length; i++) {
      var name = trim(parts[i]);
      if (!name) continue;
      acc = acc ? acc + "/" + name : name;
      var b = binCache[acc] || childBin(cur, name);
      if (!b) {
        var made = cur.createBin(name);
        b = (made && made.type === 2) ? made : childBin(cur, name);
        if (!b) throw new Error("could not create bin " + acc);
        log("bin created: " + acc);
      }
      binCache[acc] = b;
      cur = b;
    }
    return cur;
  }
  function manifestClip(path) {
    var k = norm(path);
    for (var i = 0; i < M.clips.length; i++) if (norm(M.clips[i].path) === k) return M.clips[i];
    return null;
  }
  function clipMap() {
    var m = {};
    for (var i = 0; i < M.clips.length; i++) {
      m[norm(M.clips[i].path)] = M.clips[i];
      if (M.clips[i].category_file) m[norm(M.clips[i].category_file)] = M.clips[i];
    }
    return m;
  }

  // ---------- sequences ----------
  function findSequence(name) {
    for (var i = 0; i < app.project.sequences.numSequences; i++) {
      var s = app.project.sequences[i];
      if (s.name === name || s.sequenceID === name) return s;
    }
    return null;
  }
  function uniqueSeqName(name) {
    var n = name, k = 2;
    while (findSequence(n)) { n = name + " v" + k; k++; }
    return n;
  }
  function listPresets() {
    var found = [], roots = [];
    var isWin = $.os.indexOf("Windows") >= 0;
    var base = new Folder(isWin ? "C:/Program Files/Adobe" : "/Applications");
    if (base.exists) {
      var subs = base.getFiles();
      for (var i = 0; i < subs.length; i++) {
        if (!(subs[i] instanceof Folder) || !/Adobe Premiere Pro/.test(subs[i].displayName)) continue;
        if (isWin) roots.push(new Folder(subs[i].fsName + "/Settings/SequencePresets"));
        else {
          var apps = subs[i].getFiles();
          for (var j = 0; j < apps.length; j++) if (/\.app$/.test(apps[j].displayName)) roots.push(new Folder(apps[j].fsName + "/Contents/Settings/SequencePresets"));
        }
      }
    }
    function dig(folder, depth) {
      if (depth > 4 || !folder.exists) return;
      var fs = folder.getFiles();
      for (var i = 0; i < fs.length; i++) {
        if (fs[i] instanceof Folder) dig(fs[i], depth + 1);
        else if (/\.sqpreset$/i.test(fs[i].displayName)) found.push(fs[i].fsName);
      }
    }
    for (var r = 0; r < roots.length; r++) dig(roots[r], 0);
    return found;
  }
  function pickPreset(preferred) {
    if (preferred) { var f = new File(preferred); if (f.exists) return f.fsName; }
    if (M && M.sequence && M.sequence.preset) { var g = new File(M.sequence.preset); if (g.exists) return g.fsName; }
    var all = listPresets();
    var pats = [/1080p\s*(23\.976|24)\b/i, /DSLR[\\\/].*1080p24/i, /1080p24/i, /1080p/i, /./];
    for (var p = 0; p < pats.length; p++) for (var i = 0; i < all.length; i++) if (pats[p].test(all[i])) return all[i];
    return null;
  }
  function applyHouseSettings(seq) {
    try {
      var st = seq.getSettings();
      st.videoFrameWidth = 1920; st.videoFrameHeight = 1080;
      try { st.videoFrameRate.ticks = String(FRAME_TICKS); } catch (e1) {}
      seq.setSettings(st);
    } catch (e) { log("sequence settings not changed (" + e + ") — check 1920x1080 @ 23.976 in Sequence Settings"); }
    try { seq.setZeroPoint(String(3600 * TICKS)); } catch (e2) { try { seq.zeroPoint = String(3600 * TICKS); } catch (e3) { log("start timecode not set — set 01:00:00:00 in Sequence Settings"); } }
  }
  function createSequence(name, opts, seedItem) {
    name = uniqueSeqName(name);
    var seq = null, preset = pickPreset(opts && opts.preset);
    app.enableQE();
    if (preset) {
      try {
        qe.project.newSequence(name, preset);
        seq = app.project.activeSequence;
        if (!seq || seq.name !== name) seq = findSequence(name);
      } catch (e) { log("preset sequence failed: " + e); seq = null; }
    }
    if (!seq && seedItem) {
      try { seq = app.project.createNewSequenceFromClips(name, [seedItem]); } catch (e4) { log("createNewSequenceFromClips failed: " + e4); }
      if (seq) {   // that puts the seed clip on the timeline: remove it
        try { for (var t = 0; t < seq.videoTracks.numTracks; t++) while (seq.videoTracks[t].clips.numItems) seq.videoTracks[t].clips[0].remove(false, false); } catch (e5) {}
        try { for (var a = 0; a < seq.audioTracks.numTracks; a++) while (seq.audioTracks[a].clips.numItems) seq.audioTracks[a].clips[0].remove(false, false); } catch (e6) {}
      }
    }
    if (!seq) throw new Error("could not create a sequence: no .sqpreset found (pass {preset:'<path>.sqpreset'}) and no clip to seed from");
    applyHouseSettings(seq);
    try { app.project.openSequence(seq.sequenceID); } catch (e7) {}
    try { app.project.activeSequence = seq; } catch (e8) {}
    try {   // keep the project tidy
      var pi = findSequenceItem(seq.name);
      if (pi) pi.moveBin(bin("Timelines"));
    } catch (e9) {}
    log("sequence created: " + name + (preset ? "  (preset " + basename(preset) + ")" : ""));
    return seq;
  }
  function findSequenceItem(name) {
    var hit = null;
    walk(app.project.rootItem, null, function (it) { if (!hit && it.type !== 2 && it.name === name) { try { if (it.isSequence()) hit = it; } catch (e) {} } });
    return hit;
  }
  function ensureTracks(seq, nVideo, nAudio) {
    var needV = nVideo - seq.videoTracks.numTracks, needA = nAudio - seq.audioTracks.numTracks;
    if (needV <= 0 && needA <= 0) return true;
    try {
      app.enableQE();
      var qs = qe.project.getActiveSequence();
      // addTracks(numVideo, videoIndex, numAudio, audioChannelType(1=mono,2=stereo), audioIndex, numSubmix, submixType, submixIndex)
      // audio channel type: 0 = mono, 1 = stereo, 2 = 5.1 — stereo, or Premiere shifts stereo clips onto another track
      qs.addTracks(Math.max(0, needV), seq.videoTracks.numTracks, Math.max(0, needA), 1, seq.audioTracks.numTracks, 0, 1, 0);
    } catch (e) { log("could not add tracks (" + e + "); add " + Math.max(0, needV) + " video / " + Math.max(0, needA) + " audio tracks by hand"); }
    return seq.videoTracks.numTracks >= nVideo && seq.audioTracks.numTracks >= nAudio;
  }
  function place(seq, item, srcIn, srcOut, at, vTrack, aTrack) {
    // in/out on the project item, then overwrite at `at` (seconds of sequence time, 0 = sequence start)
    var ok = false;
    try { item.setInPoint(ticks(srcIn), 4); item.setOutPoint(ticks(srcOut), 4); } catch (e) {
      try { item.setInPoint(ticks(srcIn), 1); item.setOutPoint(ticks(srcOut), 1); item.setInPoint(ticks(srcIn), 2); item.setOutPoint(ticks(srcOut), 2); } catch (e2) {}
    }
    try {
      if (typeof seq.overwriteClip === "function") { seq.overwriteClip(item, ticksFrame(at), vTrack, aTrack); ok = true; }
      else if (vTrack >= 0) { seq.videoTracks[vTrack].overwriteClip(item, at); ok = true; }
      else { seq.audioTracks[aTrack].overwriteClip(item, at); ok = true; }
    } catch (e3) { log("place failed for " + item.name + " at " + fmt(at) + ": " + e3); }
    try { item.clearInPoint(4); item.clearOutPoint(4); } catch (e4) {}
    return ok;
  }
  function clipAt(track, atSec) {       // the track clip that starts at/near atSec
    var want = Math.round(atSec * TICKS), best = null, bestD = 1e18;
    for (var i = 0; i < track.clips.numItems; i++) {
      var d = Math.abs(parseFloat(track.clips[i].start.ticks) - want);
      if (d < bestD) { bestD = d; best = track.clips[i]; }
    }
    return bestD <= FRAME_TICKS * 1.5 ? best : null;
  }
  function marker(seq, at, name, comment, color) {
    try {
      var mk = seq.markers.createMarker(at);
      mk.name = name;
      if (comment) mk.comments = comment;
      if (color !== undefined) { try { mk.setColorByIndex(color); } catch (e) {} }
      return mk;
    } catch (e2) { log("marker failed at " + fmt(at) + ": " + e2); return null; }
  }
  function qeItemFor(qeTrack, domClip, domIndex) {
    // QE track items include gaps, so match by start ticks; fall back to the DOM index (the bridge's own approach)
    var want = String(domClip.start.ticks);
    for (var i = 0; i < qeTrack.numItems; i++) {
      var q = qeTrack.getItemAt(i);
      try { if (q && q.start && String(q.start.ticks) === want && q.type !== "Empty") return q; } catch (e) {}
    }
    try { var f = qeTrack.getItemAt(domIndex); if (f && f.name === domClip.name) return f; } catch (e2) {}
    return null;
  }
  function component(clip, displayName) {
    for (var i = 0; i < clip.components.numItems; i++) if (clip.components[i].displayName === displayName) return clip.components[i];
    return null;
  }
  function property(comp, displayName) {
    for (var p = 0; p < comp.properties.numItems; p++) if (comp.properties[p].displayName === displayName) return comp.properties[p];
    return null;
  }
  function addVideoEffect(qeSeq, trackIndex, domClip, effectName, domIndex) {
    var qt = qeSeq.getVideoTrackAt(trackIndex), q = qeItemFor(qt, domClip, domIndex);
    if (!q) throw new Error("QE item not found for " + domClip.name);
    var fx = qe.project.getVideoEffectByName(effectName);
    if (!fx) throw new Error("effect not installed: " + effectName);
    q.addVideoEffect(fx);
  }
  function addAudioEffect(qeSeq, trackIndex, domClip, effectName, domIndex) {
    var qt = qeSeq.getAudioTrackAt(trackIndex), q = qeItemFor(qt, domClip, domIndex);
    if (!q) throw new Error("QE item not found for " + domClip.name);
    var fx = qe.project.getAudioEffectByName(effectName);
    if (!fx) throw new Error("audio effect not installed: " + effectName);
    q.addAudioEffect(fx);
  }
  function targetSequence(opts) {
    var seq = opts && opts.sequence ? findSequence(opts.sequence) : app.project.activeSequence;
    if (!seq) throw new Error(opts && opts.sequence ? "sequence not found: " + opts.sequence : "no active sequence (open one, or pass {sequence:'name'})");
    try { app.project.openSequence(seq.sequenceID); } catch (e0) {}   // QE reads the open, active sequence
    try { app.project.activeSequence = seq; } catch (e) {}
    return seq;
  }

  // ---------- steps ----------
  function stepStatus() {
    reindex();
    var missing = [], present = 0, byCat = {}, newOnes = [];
    var cm = clipMap();
    for (var i = 0; i < M.clips.length; i++) {
      if (M.clips[i].enhance && M.clips[i].enhance.clean) cm[norm(M.clips[i].enhance.clean)] = M.clips[i];   // cleaned WAVs are ours, not new footage
      if (itemFor(M.clips[i].path)) present++; else missing.push(M.clips[i].name);
      var c = M.clips[i].category || "(uncategorized)";
      byCat[c] = (byCat[c] || 0) + 1;
    }
    for (var k in index) if (index.hasOwnProperty(k) && !cm[k]) newOnes.push(basename(index[k].item.name));
    return { manifest: M._path, generated: M.generated, project: app.project.name, clips_in_manifest: M.clips.length, in_project: present,
             not_imported: missing.length, not_imported_names: missing.slice(0, 30),
             in_project_but_not_in_manifest: newOnes.length, new_names: newOnes.slice(0, 30),
             categories: byCat, multicam_groups: M.multicams ? M.multicams.length : 0, plan: M.plan ? M.plan.name : null, grade: M.grade ? M.grade.look : null,
             hint: newOnes.length ? "new footage in the project that the engine has not seen: re-run /buwan:assemble scan → cull → … then `assemble.js premiere` and this step again" : "" };
  }
  function stepImport(opts) {
    reindex();
    var limit = opts.limit || 150, groups = {}, order = [], todo = 0;
    for (var i = 0; i < M.clips.length; i++) {
      var c = M.clips[i];
      if (itemFor(c.path)) continue;
      var f = new File(c.path);
      if (!f.exists) { log("missing on disk: " + c.path); continue; }
      if (!groups[c.bin]) { groups[c.bin] = []; order.push(c.bin); }
      groups[c.bin].push(f.fsName); todo++;
    }
    if (M.use_clean) {
      for (var j = 0; j < M.clips.length; j++) {
        var e = M.clips[j].enhance;
        if (e && e.clean && !itemFor(e.clean) && new File(e.clean).exists) {
          if (!groups["01 Speech/Clean audio"]) { groups["01 Speech/Clean audio"] = []; order.push("01 Speech/Clean audio"); }
          groups["01 Speech/Clean audio"].push(new File(e.clean).fsName); todo++;
        }
      }
    }
    var done = 0;
    for (var g = 0; g < order.length && done < limit; g++) {
      var paths = groups[order[g]], target = bin(order[g]);
      while (paths.length && done < limit) {
        var batch = paths.splice(0, Math.min(50, limit - done));
        var ok = app.project.importFiles(batch, true, target, false);
        if (!ok) log("import returned false for " + batch.length + " files into " + order[g]);
        done += batch.length;
      }
    }
    reindex();
    return { imported: done, remaining: todo - done, hint: todo - done > 0 ? "run import again (same call) for the rest" : "" };
  }
  function stepOrganize(opts, onlyRejects) {
    reindex();
    var moved = 0, labeled = 0, missing = 0, rejects = [], warned = 0, flagged = 0;
    var flagWarnings = (opts.flag_warnings !== undefined) ? !!opts.flag_warnings : (M.flag_warnings !== false);
    for (var i = 0; i < M.clips.length; i++) {
      var c = M.clips[i];
      if (onlyRejects && !(c.reject && c.reject.length)) continue;
      var it = itemFor(c.path);
      if (!it) { missing++; continue; }
      var flagIt = flagWarnings && c.flag_bin && !(c.reject && c.reject.length);
      var target = bin(flagIt ? c.flag_bin : c.bin), parent = parentOf(c.path);
      if (!parent || parent.nodeId !== target.nodeId) {
        try { it.moveBin(target); moved++; if (flagIt) flagged++; } catch (e) { log("move failed " + c.name + ": " + e); }
      } else if (flagIt) flagged++;
      if (flagIt) { try { it.setProjectMetadata("Column.Intrinsic.Description", ["flagged: " + c.flag.join(", ") + " (was " + c.bin + ")"]); } catch (eD) {} }
      if (c.label >= 0) {
        var cur = -1; try { cur = it.getColorLabel(); } catch (e2) {}
        if (cur !== c.label) { try { it.setColorLabel(c.label); labeled++; } catch (e3) { log("label failed " + c.name + ": " + e3); } }
      }
      if (c.reject && c.reject.length) rejects.push(c.name + " (" + c.reject.join(", ") + ")");
      if (c.warn && c.warn.length) warned++;
    }
    reindex();
    return { moved: moved, labeled: labeled, not_in_project: missing, rejected: rejects.length, rejected_clips: rejects.slice(0, 40), with_warnings: warned,
             flagged: flagged, flag_bin: flagWarnings ? (M.flag_bin || "00 Flagged") : null,
             bins: M.bins, labels: M.labels, hint: missing ? "run the import step first for the " + missing + " clips not in the project" : "" };
  }
  function stepRelink(opts) {
    // Point project items at the BY_CATEGORY clones (assemble.js bycategory): master clips AND their subclips
    // (speech ranges, steady picks keep their own media path in Premiere). Same bytes, so in/out points and
    // sequence clips are unaffected. Clips trimmed to their best cut keep their RAW_COPY link (their subclips and
    // the STABILIZE ranges are timed on the full clip). Batches of items: repeat while remaining > 0.
    var start = opts.start || 0, limit = opts.limit || 150, done = 0, already = 0, kept = 0, failed = [], i;
    var dest = {}, trimmed = {};
    for (i = 0; i < M.clips.length; i++) {
      var c = M.clips[i];
      if (!c.category_file) continue;
      if (c.category_file_trimmed) trimmed[norm(c.path)] = true; else dest[norm(c.path)] = c.category_file;
    }
    var items = [];
    walk(app.project.rootItem, null, function (it) {
      if (it.type === 2) return;
      var mp = ""; try { if (it.isSequence()) return; mp = it.getMediaPath(); } catch (e) { return; }
      if (!mp) return;
      var k = norm(mp);
      if (trimmed[k]) { kept++; return; }
      if (dest[k]) items.push([it, dest[k]]);
      else if (aliasOf()[k]) already++;
    });
    var end = Math.min(items.length, start + limit);
    for (i = start; i < end; i++) {
      var it2 = items[i][0], to = items[i][1];
      if (!new File(to).exists) { failed.push(it2.name + ": category file missing"); continue; }
      try { if (it2.canChangeMediaPath && !it2.canChangeMediaPath()) throw new Error("Premiere refuses"); it2.changeMediaPath(to, true); done++; }
      catch (e1) { failed.push(it2.name + ": " + e1); }
    }
    reindex();
    return { relinked: done, already_on_by_category: already, kept_on_raw_copy_trimmed: kept, failed: failed.length, failed_clips: failed.slice(0, 20),
             still_on_raw_copy: items.length - done, remaining: Math.max(0, items.length - end),
             hint: items.length - end > 0 ? "run relink again (same call): the rest are still on RAW_COPY" : "every clip and subclip points at BY_CATEGORY" };
  }
  function lumetriLook(comp) {          // the Creative > Look popup and its loaded asset (Premiere 26.x)
    var look = null, asset = null;
    for (var p = 0; p < comp.properties.numItems; p++) {
      var pr = comp.properties[p];
      if (!look && pr.displayName === "Look") look = pr;
      if (pr.displayName === "LookAsset") asset = pr;
    }
    return { look: look, asset: asset };
  }
  function stepGrade(opts) {
    // Per camera clip: Lumetri Basic Correction > Exposure = the engine's exposure fix (assemble.js exposure), then the
    // studio look. Premiere 26.x refuses a LUT file path from a script and a list position doesn't load a user LUT, so the
    // look is copied from a reference clip where the editor picked it once (opts.look_from = "<sequence>/<clip index>"),
    // else left for one manual pick on the sequence's adjustment layer. The exposure fix never depends on the look.
    if (!M.grade || !M.grade.lut) throw new Error("no grade in the manifest: assemble.js premiere <project> --grade warm|cool|bw (and run /buwan:setup-kit for the LUTs)");
    var seq = targetSequence(opts);
    app.enableQE();
    var qeSeq = qe.project.getActiveSequence();
    reindex();
    var cm = clipMap(), lumetri = 0, skipped = 0, failed = [], exposed = 0, looked = 0, lookPending = 0;
    var start = opts.start || 0, limit = opts.limit || 100000, seen = 0;   // batches of camera clips: big sequences in several calls
    var ref = null;
    if (opts.look_from) {
      var parts = String(opts.look_from).split("/"), rs = findSequence(parts[0]), rc = rs ? rs.videoTracks[0].clips[parseInt(parts[1] || "0", 10)] : null;
      var rcomp = rc ? component(rc, "Lumetri Color") : null, rl = rcomp ? lumetriLook(rcomp) : null;
      if (rl && rl.look && rl.asset) { ref = { look: rl.look.getValue(), asset: rl.asset.getValue() }; }
      if (!ref || String(ref.asset).length < 8) throw new Error("no look picked on the reference clip " + opts.look_from + " (Lumetri > Creative > Look)");
    }
    for (var t = 0; t < seq.videoTracks.numTracks; t++) {
      var track = seq.videoTracks[t];
      for (var i = 0; i < track.clips.numItems; i++) {
        var clip = track.clips[i], mp = "";
        try { mp = clip.projectItem.getMediaPath(); } catch (e) {}
        var mc = mp ? cm[norm(mp)] : null;
        if (!mc || has(M.grade.skip_categories, mc.category) || mc.kind !== "video") { skipped++; continue; }
        seen++;
        if (seen <= start || seen > start + limit) continue;
        try {
          var comp = component(clip, "Lumetri Color");
          if (!comp) { addVideoEffect(qeSeq, t, clip, "Lumetri Color", i); comp = component(clip, "Lumetri Color"); }
          if (!comp) throw new Error("Lumetri not added");
          lumetri++;
          var ev = mc.exposure_ev || 0, expo = property(comp, "Exposure");
          if (expo) { if (Math.abs((expo.getValue() || 0) - ev) > 0.005) { expo.setValue(ev, true); } if (ev) exposed++; }
          else if (ev) failed.push(clip.name + ": no Exposure control on Lumetri");
          var lk = lumetriLook(comp);
          if (ref && lk.look && lk.asset) {
            try { lk.asset.setValue(ref.asset, true); lk.look.setValue(ref.look, true); var inten = null;
                  for (var q = comp.properties.numItems - 1; q >= 0; q--) if (comp.properties[q].displayName === "Intensity") { inten = comp.properties[q]; break; }
                  if (inten) inten.setValue(M.grade.intensity, true); looked++; }
            catch (eL) { failed.push(clip.name + ": look not copied (" + eL + ")"); lookPending++; }
          } else lookPending++;
        } catch (e4) { failed.push(clip.name + ": " + e4); }
      }
    }
    return { sequence: seq.name, look: M.grade.look, lut_file: M.grade.lut, camera_clips: seen, next_start: Math.min(seen, start + limit), remaining: Math.max(0, seen - start - limit), lumetri_clips: lumetri, exposure_fixed: exposed, look_applied: looked, look_pending: lookPending,
             skipped_non_camera: skipped, failed: failed.length, failed_clips: failed.slice(0, 20),
             hint: lookPending ? "Exposure is set. For the look: select one clip, Lumetri > Creative > Look > " + basename(M.grade.lut).replace(/\.cube$/i, "") +
                   " (installed by setup-kit), Intensity " + M.grade.intensity + ", then run grade again with {look_from:\"" + seq.name + "/<that clip's index on V1>\"}." : "" };
  }
  function stepEnhance(opts) {
    var seq = targetSequence(opts);
    app.enableQE();
    var qeSeq = qe.project.getActiveSequence();
    reindex();
    var cm = clipMap(), leveled = 0, denoised = 0, limited = 0, failed = [], seen = 0;
    for (var t = 0; t < seq.audioTracks.numTracks; t++) {
      var track = seq.audioTracks[t];
      for (var i = 0; i < track.clips.numItems; i++) {
        var clip = track.clips[i], mp = "";
        try { mp = clip.projectItem.getMediaPath(); } catch (e) {}
        var mc = mp ? cm[norm(mp)] : null;
        if (!mc || mc.category !== "01 Speech") continue;
        seen++;
        var rec = mc.enhance || { gain_db: 0, noise_reduction: 0 };
        try {
          var vol = component(clip, "Volume"), lvl = vol ? property(vol, "Level") : null;
          if (lvl && rec.gain_db) {
            var want = dB(rec.gain_db);
            lvl.setValue(want, true);
            var got = Number(lvl.getValue());
            if (!isNaN(got) && Math.abs(got - want) < 0.001) leveled++; else failed.push(clip.name + ": level write ignored");
          }
          if (rec.noise_reduction > 0 && !component(clip, "DeNoise")) {
            addAudioEffect(qeSeq, t, clip, "DeNoise", i);
            var dn = component(clip, "DeNoise"), amt = dn ? property(dn, "Amount") : null;
            if (amt) { try { amt.setValue(rec.noise_reduction, true); } catch (e1) {} }
            denoised++;
          }
          if (!component(clip, "Hard Limiter")) {
            addAudioEffect(qeSeq, t, clip, "Hard Limiter", i);
            var hl = component(clip, "Hard Limiter"), mx = hl ? property(hl, "Maximum Amplitude") : null;
            if (mx) { try { mx.setValue(-6, true); } catch (e2) {} }
            limited++;
          }
        } catch (e3) { failed.push(clip.name + ": " + e3); }
      }
    }
    return { sequence: seq.name, speech_clips: seen, leveled: leveled, denoised: denoised, limited: limited, failed: failed.length, failed_clips: failed.slice(0, 20),
             targets: "dialogue -17 LUFS, peaks -6 dBFS; verify with Essential Sound > Loudness > Auto-Match on the dialogue clips, then Window > Loudness Radar on the mix",
             hint: seen === 0 ? "no 01 Speech clips in this sequence (categories come from /buwan:organize)" : "" };
  }
  function stepDeadair(opts) {
    reindex();
    var limit = opts.limit || 400, made = 0, exists = 0, missing = 0, clipsDone = 0;
    var target = bin("01 Speech/Speech ranges"), names = {};
    for (var i = 0; i < target.children.numItems; i++) names[target.children[i].name] = true;
    for (var c = 0; c < M.clips.length && made < limit; c++) {
      var mc = M.clips[c];
      if (!mc.speech_ranges || !mc.speech_ranges.length) continue;
      var it = itemFor(mc.path);
      if (!it) { missing++; continue; }
      clipsDone++;
      for (var r = 0; r < mc.speech_ranges.length && made < limit; r++) {
        var a = mc.speech_ranges[r][0], b = mc.speech_ranges[r][1];
        var nm = mc.name + " - speech " + (r + 1 < 10 ? "0" : "") + (r + 1) + " [" + fmt(a) + "-" + fmt(b) + "]";
        if (names[nm]) { exists++; continue; }
        try {
          var sub = it.createSubClip(nm, ticks(a), ticks(b), 0, 1, 1);
          if (sub) { try { sub.moveBin(target); } catch (e) {} try { sub.setColorLabel(M.labels["01 Speech"]); } catch (e2) {} made++; names[nm] = true; }
        } catch (e3) { log("subclip failed " + nm + ": " + e3); }
      }
    }
    reindex();
    return { speech_clips: clipsDone, subclips_created: made, already_there: exists, not_in_project: missing, bin: "01 Speech/Speech ranges",
             hint: made >= limit ? "run deadair again for the rest" : "" };
  }
  function orderedSpeech() {
    var list = [];
    for (var i = 0; i < M.clips.length; i++) if (M.clips[i].speech_ranges && M.clips[i].speech_ranges.length) list.push(M.clips[i]);
    list.sort(function (x, y) {
      var a = x.sync_offset === null || x.sync_offset === undefined ? 1e12 : x.sync_offset, b = y.sync_offset === null || y.sync_offset === undefined ? 1e12 : y.sync_offset;
      return a !== b ? a - b : (x.name < y.name ? -1 : 1);
    });
    return list;
  }
  function stepAroll(opts) {
    reindex();
    var list = orderedSpeech();
    if (!list.length) throw new Error("no speech ranges in the manifest (run assemble.js deadair first)");
    var seed = null;
    for (var s = 0; s < list.length && !seed; s++) seed = itemFor(list[s].path);
    if (!seed) throw new Error("speech clips are not in the project yet — run the import step");
    var seq = createSequence(opts.name || "A-Roll clean", opts, seed);
    var t = 0, placed = 0, missing = 0, gap = opts.gap === undefined ? 0.3 : opts.gap;
    for (var i = 0; i < list.length; i++) {
      var mc = list[i], it = itemFor(mc.path);
      if (!it) { missing++; continue; }
      for (var r = 0; r < mc.speech_ranges.length; r++) {
        var a = mc.speech_ranges[r][0], b = mc.speech_ranges[r][1];
        if (place(seq, it, a, b, t, 0, 0)) { placed++; if (r === 0) marker(seq, t, mc.name, "speech " + fmt(a) + "-" + fmt(b) + (mc.camera ? " · " + mc.camera : ""), 7); }
        t += (b - a) + gap;
      }
    }
    return { sequence: seq.name, segments: placed, minutes: Math.round(t / 6) / 10, clips_not_in_project: missing };
  }
  function stepSync(opts) {
    reindex();
    if (!M.multicams || !M.multicams.length) throw new Error("no multicam groups in the manifest (run assemble.js sync first)");
    var out = [];
    for (var g = 0; g < M.multicams.length; g++) {
      var mc = M.multicams[g];
      if (opts.group && mc.id !== opts.group && mc.name !== opts.group) continue;
      if (findSequence("SYNC " + mc.name)) { out.push({ group: mc.name, sequence: "SYNC " + mc.name, skipped: "exists" }); continue; }
      var seed = null;
      for (var a0 = 0; a0 < mc.angles.length && !seed; a0++) for (var c0 = 0; c0 < mc.angles[a0].clips.length && !seed; c0++) seed = itemFor(mc.angles[a0].clips[c0].clip);
      if (!seed) { out.push({ group: mc.name, error: "clips not in project" }); continue; }
      var seq = createSequence("SYNC " + mc.name, opts, seed);
      ensureTracks(seq, mc.angles.length, mc.angles.length);
      var placed = 0, missing = 0;
      for (var a = 0; a < mc.angles.length; a++) {
        var v = Math.min(a, seq.videoTracks.numTracks - 1), au = Math.min(a, seq.audioTracks.numTracks - 1);
        for (var c = 0; c < mc.angles[a].clips.length; c++) {
          var e = mc.angles[a].clips[c], it = itemFor(e.clip);
          if (!it) { missing++; continue; }
          var m2 = manifestClip(e.clip), dur = m2 ? m2.duration : 0;
          if (place(seq, it, 0, dur, e.offset, v, au)) placed++;
        }
        marker(seq, a * 1.0, "Angle " + (a + 1) + ": " + mc.angles[a].name, "V" + (v + 1) + "/A" + (au + 1), 6);
      }
      out.push({ group: mc.name, sequence: seq.name, angles: mc.angles.length, clips_placed: placed, missing: missing });
    }
    return { sync_sequences: out, next: "In the Project panel select each SYNC sequence → right-click → Multi-Camera → Enable, then edit it as a multicam clip (Program Monitor → Multi-Camera view)." };
  }
  function stepSteady(opts) {
    // Shaky Creative/Glider clips, best cut first: best-cut -> subclip in <category>/Steady picks (no stabilizing);
    // warp (gimbal shots only) -> the best cut of the clip placed in the STABILIZE sequence with Warp Stabilizer applied.
    // handheld / too-shaky -> left in 00 Flagged/Heavy motion, not stabilized.
    reindex();
    var picks = 0, warped = 0, missing = 0, exists = 0, failed = [], seq = null, t = 0;
    var warpList = [];
    for (var i = 0; i < M.clips.length; i++) {
      var c = M.clips[i], st = c.steady;
      if (!st) continue;
      var it = itemFor(c.path);
      if (!it) { missing++; continue; }
      if (st.decision === "best-cut" && st.range) {
        var target = bin((c.category || c.bin) + "/Steady picks"), nm = c.name + " - steady [" + fmt(st.range[0]) + "-" + fmt(st.range[1]) + "]";
        var dup = false;
        for (var k = 0; k < target.children.numItems; k++) if (target.children[k].name === nm) dup = true;
        if (dup) { exists++; continue; }
        try {
          var sub = it.createSubClip(nm, ticks(st.range[0]), ticks(st.range[1]), 0, 1, 1);
          if (sub) { try { sub.moveBin(target); } catch (e) {} if (c.label >= 0) { try { sub.setColorLabel(c.label); } catch (e2) {} } picks++; }
        } catch (e3) { failed.push(nm + ": " + e3); }
      } else if (st.decision === "warp") {
        warpList.push({ clip: c, item: it });
      }
    }
    if (warpList.length) {
      seq = findSequence(opts.name || "STABILIZE - Warp") || createSequence(opts.name || "STABILIZE - Warp", opts, warpList[0].item);
      app.enableQE();
      var qs = qe.project.getActiveSequence();
      for (var w = 0; w < warpList.length; w++) {
        var wc = warpList[w];
        var wr = wc.clip.steady.range, w0 = wr ? wr[0] : 0, w1 = wr ? wr[1] : wc.clip.duration;
        if (place(seq, wc.item, w0, w1, t, 0, 0)) {
          var dom = clipAt(seq.videoTracks[0], t);
          try { addVideoEffect(qs, 0, dom, "Warp Stabilizer", seq.videoTracks[0].clips.numItems - 1); warped++; }
          catch (e4) { failed.push(wc.clip.name + ": Warp Stabilizer not applied (" + e4 + ")"); marker(seq, t, "WARP: apply by hand", "Effects > Distort > Warp Stabilizer", 3); }
          marker(seq, t, wc.clip.name, wc.clip.steady.reason || "", 7);
          t += (w1 - w0) + 0.5;
        }
      }
    }
    return { steady_picks: picks, already_there: exists, warp_clips: warped, stabilize_sequence: seq ? seq.name : null, not_in_project: missing, failed: failed.length, failed_clips: failed.slice(0, 20),
             next: "Steady picks sit next to their category bin. Only gimbal shots are stabilized, on their best cut: open the STABILIZE sequence once so Warp Stabilizer analyses in the background; copy a stabilized clip from there into your cut. Handheld shaky clips stay in 00 Flagged/Heavy motion." };
  }
  function stepSkeleton(opts) {
    // The empty same-day assembly sequence: the editor drops picks on V1 and goes.
    reindex();
    var K = M.skeleton || {}, name = opts.name || K.name || "SDE_ASSEMBLY_v1";
    var seed = null;
    for (var i = 0; i < M.clips.length && !seed; i++) if (M.clips[i].kind === "video") seed = itemFor(M.clips[i].path);
    if (!seed) throw new Error("no video clip in the project to seed a sequence from — run the import step first");
    var seq = createSequence(name, opts, seed);
    ensureTracks(seq, 3, 3);
    var sections = K.sections || ["INTRO", "STORYLINE", "CEREMONY", "OUTRO"];
    var targetMin = (K.target_min && K.target_min[1]) || 5, span = targetMin * 60 / sections.length;
    for (var k = 0; k < sections.length; k++) marker(seq, k * span, sections[k], "section", 2);
    marker(seq, 0, "TARGETS", (K.notes || "dialogue -17 LUFS, peaks -6 dBFS, music bed -20 dB") + "; target " + ((K.target_min || [4, 5]).join("-")) + " min", 1);
    marker(seq, 0.5, "V2: adjustment layer + studio look", "File > New > Adjustment Layer, drag to V2 over the full length, Lumetri > Creative > Look = Buwan LUT (or run the grade step once clips are on V1)", 3);
    marker(seq, 1.0, "V3: letterbox 2.39:1", "kit clip 'letterbox' from kit/overlays on V3 (" + (K.letterbox_px || 110) + " px bars at 1080p)", 3);
    var musicPlaced = 0, bedDb = (K.music_bed_db !== undefined) ? K.music_bed_db : -20;
    if (M.music) {
      var m2 = M.music.main || M.music.intro;
      if (m2 && m2.path) {
        var mi = itemFor(m2.path);
        if (mi && place(seq, mi, 0, m2.duration || 300, 0, -1, 2)) {
          musicPlaced++;
          var mc = clipAt(seq.audioTracks[2], 0);
          if (mc) { var vm = component(mc, "Volume"), lm = vm ? property(vm, "Level") : null; if (lm) { try { lm.setValue(dB(bedDb), true); } catch (e1) { log("music level not set: " + e1); } } }
          marker(seq, 0, "A3 music bed " + bedDb + " dB", "placeholder — swap for the final track", 0);
        }
      }
    }
    return { sequence: seq.name, sections: sections, music_bed: musicPlaced, music_bed_db: bedDb,
             next: "V1 is empty on purpose. Listen through the A-Roll clean, mark the lines, drop the picks on V1 between the section markers. Orange markers are the two hand steps (adjustment layer, letterbox)." };
  }
  function stepBuild(opts) {
    if (!M.plan) throw new Error("no plan in the manifest: assemble.js premiere <project> --plan edit/<cut>.plan.json");
    reindex();
    var P = M.plan, cm = clipMap();
    var seed = null;
    for (var s = 0; s < P.spine.length && !seed; s++) if (!P.spine[s].gap) seed = itemFor(P.spine[s].clip);
    for (var s2 = 0; s2 < P.connected.length && !seed; s2++) seed = itemFor(P.connected[s2].clip);
    if (!seed) throw new Error("plan clips are not in the project — run the import step");
    var seq = createSequence(opts.name || P.name, opts, seed);
    var useClean = !!M.use_clean;
    // V1 speech, V2 b-roll | A1 speech, A2 clean speech (optional), A3 music intro, A4 music story
    var A_CLEAN = 1, A_INTRO = useClean ? 2 : 1, A_STORY = useClean ? 3 : 2;
    // b-roll natural sound gets its own muted track: overwriteClip(item, t, v, -1) still lays linked audio on A1 and cuts the speech
    var A_NAT = A_STORY + 1;
    ensureTracks(seq, 2, A_NAT + 1);
    try { seq.audioTracks[A_NAT].name = "B-roll nat sound"; seq.audioTracks[A_NAT].setMute(1); } catch (eN) {}
    var placedSpeech = 0, placedBroll = 0, placedMusic = 0, missing = [], slowmo = [], levelFails = 0;
    // speech spine
    for (var i = 0; i < P.spine.length; i++) {
      var sp = P.spine[i];
      for (var k = 0; sp.markers && k < sp.markers.length; k++) {
        var mk = sp.markers[k];
        marker(seq, sp.at + mk.t, mk.name, mk.todo ? "TODO" : "", mk.chapter ? 2 : (mk.todo ? 3 : (/PEAK|HOLD/.test(mk.name) ? 1 : 0)));
      }
      if (sp.gap) continue;
      var it = itemFor(sp.clip);
      if (!it) { missing.push(basename(sp.clip)); continue; }
      if (place(seq, it, sp["in"], sp.out, sp.at, 0, 0)) {
        placedSpeech++;
        if (useClean) {
          var mcs = cm[norm(sp.clip)], cl = mcs && mcs.enhance && mcs.enhance.clean ? itemFor(mcs.enhance.clean) : null;
          if (cl) {
            place(seq, cl, sp["in"], sp.out, sp.at, -1, A_CLEAN);
            var camA = clipAt(seq.audioTracks[0], sp.at);          // mute the camera audio under it
            if (camA) { var v0 = component(camA, "Volume"), l0 = v0 ? property(v0, "Level") : null; if (l0) { try { l0.setValue(0, true); } catch (e0) {} } }
          }
        }
      }
    }
    // b-roll + music
    for (var j = 0; j < P.connected.length; j++) {
      var c = P.connected[j], item = itemFor(c.clip);
      if (!item) { missing.push(basename(c.clip)); continue; }
      if (c.role === "music") {
        var isIntro = /intro/i.test(c.name || ""), aT = isIntro ? A_INTRO : A_STORY;
        if (place(seq, item, c["in"], c.out, c.at, -1, aT)) {
          placedMusic++;
          var mclip = clipAt(seq.audioTracks[aT], c.at), gdb = (c.gain_db !== undefined && c.gain_db !== null) ? c.gain_db : (isIntro ? -3 : -20);
          if (mclip) { var vm = component(mclip, "Volume"), lm = vm ? property(vm, "Level") : null; if (lm) { try { lm.setValue(dB(gdb), true); if (Math.abs(Number(lm.getValue()) - dB(gdb)) > 0.001) levelFails++; } catch (e1) { levelFails++; } } }
          marker(seq, c.at, (c.name || "Music") + " " + gdb + " dB", "music bed " + gdb + " dB", 0);
        }
        continue;
      }
      var mcc = cm[norm(c.clip)], a = c["in"], b = c.out;
      if (c.slowmo && mcc && mcc.fps > 24.5) {
        var factor = mcc.fps / (24000 / 1001);
        try { item.setOverrideFrameRate(24000 / 1001); a = c["in"] * factor; b = c.out * factor; if (!has(slowmo, item.name)) slowmo.push(item.name); } catch (e2) { marker(seq, c.at, "SPEED: slow-mo " + Math.round(100 / factor) + "% — set by hand", "Clip > Speed/Duration", 3); }
      }
      if (place(seq, item, a, b, c.at, 1, A_NAT)) placedBroll++;
    }
    var st = P.stats || {};
    return { sequence: seq.name, speech_clips: placedSpeech, broll_shots: placedBroll, music: placedMusic, slowmo_interpreted: slowmo.length, slowmo_clips: slowmo.slice(0, 20),
             music_level_writes_failed: levelFails, missing: missing.length, missing_names: missing.slice(0, 20), total_s: st.total_s || 0, lines: st.speech_lines || 0,
             edl: P.edl || null, notes: P.notes || [],
             next: "Open the sequence; chapter markers (purple) mark the parts, red = peak/final hold, orange = graphics TODO (render with /buwan:graphics). Run grade and enhance on this sequence next." };
  }

  function run(step, manifestPath, opts) {
    logs = [];
    var t0 = new Date().getTime();
    try {
      if (!app.project) throw new Error("no project open in Premiere");
      loadManifest(manifestPath);
      var o = parseOpts(opts), r;
      switch (String(step)) {
        case "status": r = stepStatus(o); break;
        case "import": r = stepImport(o); break;
        case "organize": r = stepOrganize(o, false); break;
        case "cull": r = stepOrganize(o, true); break;
        case "grade": r = stepGrade(o); break;
        case "relink": r = stepRelink(o); break;
        case "enhance": r = stepEnhance(o); break;
        case "deadair": r = stepDeadair(o); break;
        case "aroll": r = stepAroll(o); break;
        case "sync": r = stepSync(o); break;
        case "steady": r = stepSteady(o); break;
        case "skeleton": r = stepSkeleton(o); break;
        case "build": r = stepBuild(o); break;
        case "basics":
          // the same-day scope: import, organize (bins + labels, rejects, flagged), dead air, A-Roll clean, steady. No sync, no sequences to cut in.
          r = { "import": stepImport({ limit: 100000 }), organize: stepOrganize(o, false), deadair: stepDeadair({ limit: 100000 }) };
          try { r.aroll = stepAroll(o); } catch (eB1) { r.aroll = { error: String(eB1) }; }
          try { r.steady = stepSteady(o); } catch (eB2) { r.steady = { error: String(eB2) }; }
          if (M.clips.length && M.clips[0].category_file !== undefined) {
            try { r.relink = stepRelink({ limit: 100000 }); } catch (eB3) { r.relink = { error: String(eB3) }; }
          }
          if (M.grade && M.grade.lut) {   // the Buwan look + per-clip exposure on the sequences the basics made (no editor sequences)
            r.grade = {};
            var gs = ["A-Roll clean", "STABILIZE - Warp"];
            for (var g = 0; g < gs.length; g++) { if (findSequence(gs[g])) { try { r.grade[gs[g]] = stepGrade({ sequence: gs[g] }); } catch (eB4) { r.grade[gs[g]] = { error: String(eB4) }; } } }
          }
          r.next = "Basics done. Multicam sync (/buwan:multicam), the story (/buwan:plot) and the cut are the editor's call.";
          break;
        case "all":
          r = { "import": stepImport({ limit: 100000 }), organize: stepOrganize(o, false), deadair: stepDeadair({ limit: 100000 }) };
          r.aroll = stepAroll(o);
          if (M.multicams && M.multicams.length) { try { r.sync = stepSync(o); } catch (e1) { r.sync = { error: String(e1) }; } }
          if (M.plan) {
            r.build = stepBuild(o);
            var so = { sequence: r.build.sequence };
            if (M.grade && M.grade.lut) { try { r.grade = stepGrade(so); } catch (e2) { r.grade = { error: String(e2) }; } }
            try { r.enhance = stepEnhance(so); } catch (e3) { r.enhance = { error: String(e3) }; }
          }
          break;
        default: throw new Error("unknown step: " + step + " (status, import, organize, cull, relink, grade, enhance, deadair, aroll, steady, sync, skeleton, build, basics, all)");
      }
      r.ok = true; r.step = step; r.seconds = Math.round((new Date().getTime() - t0) / 100) / 10; r.log = logs;
      try { app.project.save(); r.saved = true; } catch (e4) { r.saved = false; }
      return r;
    } catch (err) {
      return { ok: false, step: step, error: String(err), line: err && err.line ? err.line : null, log: logs };
    }
  }

  return { run: run, version: "1.5.0", steps: ["status", "import", "organize", "cull", "relink", "grade", "enhance", "deadair", "aroll", "steady", "sync", "skeleton", "build", "basics", "all"] };
})();
