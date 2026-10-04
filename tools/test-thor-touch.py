#!/usr/bin/env python3
"""Compile and exercise the gesture recognizer shipped in the frontend patch."""

from pathlib import Path
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def check_sway_filters():
    scripts = ROOT / "multi-pop-thor/scripts"
    activation = (scripts / "enable_multi_pop_thor.sh").read_text()
    reboot = (scripts / "start_after_reboot.sh").read_text()
    # Exercise the actual embedded filters against stock and unrelated input directives.
    filters = [
        activation.split("awk -v stock_exec=", 1)[1].split("'\n", 1)[1].split("\n' \"$SWAY_CONFIG\"", 1)[0],
        reboot.split("awk '\n", 1)[1].split("\n' \"$config\"", 1)[0],
    ]
    stock = 'exec_always swaymsg input "0:0:bottom_touchscreen" events disabled'
    top = 'exec_always swaymsg input "0:0:top_touchscreen" events disabled'
    mapping = 'exec_always swaymsg input "0:0:bottom_touchscreen" map_to_output DSI-1'
    fixture = "\n".join([stock, "  " + stock.replace(" ", "  ") + "  ", top, mapping, "# " + stock, "output DSI-1 power off"]) + "\n"
    for program in filters:
        result = subprocess.run(["awk", program], input=fixture, text=True, capture_output=True, check=True).stdout
        assert result == "\n".join([top, mapping, "# " + stock]) + "\n", result
        assert subprocess.run(["awk", program], input=result, text=True, capture_output=True, check=True).stdout == result
    fragment = activation.split("<<'SWAY'\n", 1)[1].split("\nSWAY", 1)[0]
    assert 'input "0:0:bottom_touchscreen" events enabled' in fragment
    assert 'input "0:0:bottom_touchscreen" map_to_output DSI-1' in fragment
    print("Sway checks passed: stock override removed, other inputs preserved, repeat activation unchanged")


def main():
    check_sway_filters()
    back = ET.parse(ROOT / "multi-pop-thor/layouts/games.xml").find(".//text[@name='library-back']")
    x, y = map(float, back.findtext("pos").split())
    width, height = map(float, back.findtext("size").split())
    assert [round(x * 4400), round(y * 1080), round(width * 4400), round(height * 1080)] == [3188, 16, 136, 100]
    top_back = ET.parse(ROOT / "multi-pop-thor/layouts/games.xml").find(".//text[@name='top-library-back']")
    x, y = map(float, top_back.findtext("pos").split())
    width, height = map(float, top_back.findtext("size").split())
    assert [round(x * 4400), round(y * 1080), round(width * 4400), round(height * 1080)] == [1268, 16, 136, 100]
    compiler = shutil.which("c++")
    if compiler is None:
        raise SystemExit("Install a C++ compiler: xcode-select --install on macOS, or sudo pacman -S base-devel on Arch")
    patch = (ROOT / "multi-pop-thor/frontend/thor-game-paging.patch").read_text()
    marker = "--- /dev/null\n+++ b/es-core/src/components/ThorTouchGesture.h\n"
    header_patch = marker + patch.split(marker, 1)[1]
    with tempfile.TemporaryDirectory(prefix="multi-pop-touch-") as directory:
        work = Path(directory)
        subprocess.run(["patch", "-p1", "--batch"], input=header_patch, text=True, cwd=work, check=True, stdout=subprocess.DEVNULL)
        source = work / "test.cpp"
        source.write_text(r'''#include "es-core/src/components/ThorTouchGesture.h"
#include <cassert>
#include <iostream>

int main()
{
    assert(ThorTouchGesture::libraryBackHit(1336, 66));
    assert(!ThorTouchGesture::libraryBackHit(1267, 66));
    assert(!ThorTouchGesture::libraryBackHit(1404, 66));
    ThorTouchGesture topBack;
    topBack.begin(1336, 66, 100, 1240, 3160);
    assert(topBack.move(1340, 68) == 0);
    assert(topBack.tap(200));
    assert(ThorTouchGesture::libraryBackHit(3256, 66));
    assert(!ThorTouchGesture::libraryBackHit(3187, 66));
    assert(!ThorTouchGesture::libraryBackHit(3324, 66));
    assert(!ThorTouchGesture::libraryBackHit(3256, 116));
    ThorTouchGesture back;
    back.begin(3256, 66, 100);
    back.move(3259, 68);
    assert(back.tap(200));
    back.begin(3256, 66, 100);
    back.move(3310, 66);
    assert(!back.tap(200));

    ThorTouchTargets cards;
    cards.add(8, 3212, 232, 310, 500);
    cards.add(0, 4038, 232, 310, 500);
    cards.add(9, 3602, 195, 356, 575);
    assert(cards.hit(3367, 500) == 8);
    assert(cards.hit(3780, 500) == 9);
    assert(cards.hit(4193, 500) == 0);
    assert(cards.hit(3550, 500) == -1);
    assert(cards.hit(3780, 100) == -1);
    cards.add(3, 3700, 300, 100, 100);
    assert(cards.hit(3750, 350) == 3);
    cards.clear();
    assert(cards.hit(3780, 500) == -1);

    ThorTouchGesture upper;
    upper.begin(2200, 540, 100, 1240, 3160);
    assert(upper.move(2100, 540) == 1);
    assert(!upper.tap(200));
    upper.begin(2200, 540, 100, 1240, 3160);
    assert(upper.move(2300, 540) == -1);
    assert(!upper.tap(200));
    upper.begin(2200, 540, 100, 1240, 3160);
    assert(upper.move(2205, 542) == 0);
    assert(upper.tap(200));
    upper.begin(3150, 540, 100, 1240, 3160);
    assert(upper.move(3170, 540) == 0);
    assert(!upper.tap(200));

    ThorTouchGesture gesture;
    gesture.begin(3780, 540, 100);
    assert(gesture.move(3787, 546) == 0);
    assert(gesture.tap(250));

    gesture.begin(3780, 540, 100);
    assert(gesture.move(3681, 540) == 0);
    assert(gesture.move(3680, 540) == 1);
    assert(gesture.move(3480, 540) == 2);
    assert(!gesture.tap(250));
    assert(gesture.move(3580, 540) == -1);

    gesture.begin(3780, 540, 100);
    assert(gesture.move(3880, 540) == -1);
    assert(!gesture.tap(250));

    // Returning to the starting point after movement must not launch the item.
    gesture.begin(3780, 540, 100);
    gesture.move(3800, 540);
    gesture.move(3780, 540);
    assert(!gesture.tap(250));

    gesture.begin(3780, 540, 100);
    assert(!gesture.tap(601));

    gesture.begin(3780, 540, 100);
    assert(gesture.move(3785, 570) == 0);
    assert(gesture.move(3580, 540) == 0);
    assert(!gesture.tap(250));

    gesture.begin(3180, 540, 100);
    assert(gesture.move(3159, 540) == 0);
    assert(gesture.move(3300, 540) == 0);
    assert(!gesture.tap(250));

    gesture.begin(3780, 1060, 100);
    assert(gesture.move(3780, 1080) == 0);
    assert(!gesture.tap(250));

    gesture.begin(3780, 540, 100);
    gesture.cancel();
    assert(gesture.move(3580, 540) == 0);
    assert(!gesture.tap(250));

    gesture.begin(3780, 540, UINT32_MAX - 100);
    assert(gesture.tap(50));
    assert(!gesture.tap(500));
    std::cout << "Touch checks passed: jitter, both directions, continuous swipes, reversal, no accidental taps, long press, vertical movement, bounds, cancellation, timer wrap\n";
}
''')
        binary = work / "test"
        subprocess.run([compiler, "-std=c++11", "-Wall", "-Wextra", "-Werror", str(source), "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True)


if __name__ == "__main__":
    main()
