import os
import pcbnew

_order_ids = []
_order_timer = None


def _typed(item):
    if item.GetClass() == "FOOTPRINT":
        return item.Cast()
    try:
        return item.Cast()
    except TypeError:
        return item


def _bbox(item):
    typed = _typed(item)
    if typed.GetClass() == "FOOTPRINT":
        return typed.GetBoundingBox(False)
    return typed.GetBoundingBox()


def _iter_selection():
    selection = pcbnew.GetCurrentSelection()
    iterator = selection.iterator()
    while True:
        try:
            yield iterator.next()
        except StopIteration:
            return


def _item_id(item):
    return item.m_Uuid.AsString()


def _resolve_item(item):
    item_class = item.GetClass()
    if item_class == "PAD":
        parent = item.GetParent()
        if parent is not None:
            return parent
    if item_class == "PCB_MARKER":
        return None
    return item


def update_selection_order():
    global _order_ids
    current = []
    seen = set()
    for raw in _iter_selection():
        item = _resolve_item(raw)
        if item is None:
            continue
        uid = _item_id(item)
        if uid in seen:
            continue
        seen.add(uid)
        current.append(uid)
    current_set = set(current)
    _order_ids = [uid for uid in _order_ids if uid in current_set]
    known = set(_order_ids)
    for uid in current:
        if uid not in known:
            _order_ids.append(uid)


def start_order_tracker():
    global _order_timer
    if _order_timer is not None:
        return
    try:
        import wx
    except ImportError:
        return

    def try_start():
        global _order_timer
        if wx.GetApp() is None:
            wx.CallLater(400, try_start)
            return
        timer = wx.Timer()
        timer.Bind(wx.EVT_TIMER, lambda event: update_selection_order())
        timer.Start(120)
        _order_timer = timer
        update_selection_order()

    try:
        wx.CallAfter(try_start)
    except Exception:
        try_start()


def _selected_items():
    update_selection_order()
    items = []
    seen = set()
    for raw in _iter_selection():
        item = _resolve_item(raw)
        if item is None:
            continue
        uid = _item_id(item)
        if uid in seen:
            continue
        seen.add(uid)
        items.append(item)
    order_index = {uid: index for index, uid in enumerate(_order_ids)}
    items.sort(key=lambda item: order_index.get(_item_id(item), 10 ** 9))
    footprints = [item for item in items if item.GetClass() == "FOOTPRINT"]
    if len(footprints) >= 2:
        return footprints
    return items


def _skip_child(item):
    parent = item.GetParent()
    return parent is not None and parent.IsSelected()


def _align(axis, edge):
    items = _selected_items()
    if len(items) < 2:
        return
    reference = items[0]
    ref_box = _bbox(reference)
    if edge == "left":
        target = ref_box.GetLeft()
        delta = lambda box: pcbnew.VECTOR2I(target - box.GetLeft(), 0)
    elif edge == "right":
        target = ref_box.GetRight()
        delta = lambda box: pcbnew.VECTOR2I(target - box.GetRight(), 0)
    elif edge == "top":
        target = ref_box.GetTop()
        delta = lambda box: pcbnew.VECTOR2I(0, target - box.GetTop())
    elif edge == "bottom":
        target = ref_box.GetBottom()
        delta = lambda box: pcbnew.VECTOR2I(0, target - box.GetBottom())
    elif edge == "hcenter":
        target = ref_box.GetCenter().x
        delta = lambda box: pcbnew.VECTOR2I(target - box.GetCenter().x, 0)
    else:
        target = ref_box.GetCenter().y
        delta = lambda box: pcbnew.VECTOR2I(0, target - box.GetCenter().y)
    for item in items[1:]:
        if item.IsLocked() or _skip_child(item):
            continue
        item.Move(delta(_bbox(item)))
    pcbnew.Refresh()


def _distribute(axis, mode):
    items = _selected_items()
    if len(items) < 3:
        return
    movable = [item for item in items if not item.IsLocked() and not _skip_child(item)]
    if len(movable) < 3:
        return
    entries = [(item, _bbox(item)) for item in movable]
    if axis == "x":
        entries.sort(key=lambda entry: entry[1].GetCenter().x)
        if mode == "centers":
            first = entries[0][1].GetCenter().x
            last = entries[-1][1].GetCenter().x
            step = (last - first) / float(len(entries) - 1)
            for index, (item, box) in enumerate(entries[1:-1], start=1):
                item.Move(pcbnew.VECTOR2I(int(first + step * index) - box.GetCenter().x, 0))
        else:
            span = entries[-1][1].GetLeft() - entries[0][1].GetRight()
            inner = sum(box.GetRight() - box.GetLeft() for _, box in entries[1:-1])
            gap = (span - inner) / float(len(entries) - 1)
            cursor = entries[0][1].GetRight()
            for item, box in entries[1:-1]:
                cursor += gap
                item.Move(pcbnew.VECTOR2I(int(cursor) - box.GetLeft(), 0))
                cursor += box.GetRight() - box.GetLeft()
    else:
        entries.sort(key=lambda entry: entry[1].GetCenter().y)
        if mode == "centers":
            first = entries[0][1].GetCenter().y
            last = entries[-1][1].GetCenter().y
            step = (last - first) / float(len(entries) - 1)
            for index, (item, box) in enumerate(entries[1:-1], start=1):
                item.Move(pcbnew.VECTOR2I(0, int(first + step * index) - box.GetCenter().y))
        else:
            span = entries[-1][1].GetTop() - entries[0][1].GetBottom()
            inner = sum(box.GetBottom() - box.GetTop() for _, box in entries[1:-1])
            gap = (span - inner) / float(len(entries) - 1)
            cursor = entries[0][1].GetBottom()
            for item, box in entries[1:-1]:
                cursor += gap
                item.Move(pcbnew.VECTOR2I(0, int(cursor) - box.GetTop()))
                cursor += box.GetBottom() - box.GetTop()
    pcbnew.Refresh()


def run_action(action):
    if action == "left":
        _align("x", "left")
    elif action == "hcenter":
        _align("x", "hcenter")
    elif action == "right":
        _align("x", "right")
    elif action == "top":
        _align("y", "top")
    elif action == "vcenter":
        _align("y", "vcenter")
    elif action == "bottom":
        _align("y", "bottom")
    elif action == "dist_h_centers":
        _distribute("x", "centers")
    elif action == "dist_h_gaps":
        _distribute("x", "gaps")
    elif action == "dist_v_centers":
        _distribute("y", "centers")
    elif action == "dist_v_gaps":
        _distribute("y", "gaps")


ICON_FILES = {
    "left": "left",
    "hcenter": "hcenter",
    "right": "right",
    "top": "top",
    "vcenter": "vcenter",
    "bottom": "bottom",
    "dist_h_centers": "dist_h_centers",
    "dist_h_gaps": "dist_h_gaps",
    "dist_v_centers": "dist_v_centers",
    "dist_v_gaps": "dist_v_gaps",
}


def icon_path(name, dark=False):
    file_name = ICON_FILES[name] + ("_dark.png" if dark else ".png")
    return os.path.join(os.path.dirname(__file__), "icons", file_name)
# AI
