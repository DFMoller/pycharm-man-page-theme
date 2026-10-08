import java.awt.Dimension;
import java.awt.Robot;
import java.awt.Toolkit;
import java.awt.event.InputEvent;
import java.awt.event.KeyEvent;
import java.util.ArrayList;
import java.util.List;

/**
 * Presses key chords on the X display named by DISPLAY.
 *
 * <p>Each argument is one chord, such as {@code ctrl+alt+s} or {@code shift}. Key names are the
 * {@link KeyEvent} constants without the {@code VK_} prefix, in any case, plus the short forms
 * {@code ctrl} and {@code esc}. Run it with the Java runtime bundled in PyCharm as a single source
 * file: {@code <pycharm>/jbr/bin/java preview/Keys.java ctrl+alt+s}.
 */
public class Keys {
    // Long enough for the IDE to see two presses of the same key as separate presses (for double Shift).
    private static final int DELAY_MS = 120;
    // Height of a point inside the IDE's header bar, measured from the top of the screen.
    private static final int HEADER_Y = 20;

    public static void main(String[] args) throws Exception {
        // On a Wayland session, Robot asks the desktop for access to the user's real screen and keyboard
        // instead of using the virtual X display. Never let that happen.
        for (String name : new String[] {"WAYLAND_DISPLAY", "XDG_SESSION_TYPE"}) {
            if (System.getenv(name) != null) {
                System.err.println("Keys: refusing to run with " + name + " set; unset it to use DISPLAY only.");
                System.exit(2);
            }
        }
        Robot robot = new Robot();
        robot.setAutoDelay(20);
        // There is no window manager on the virtual display to give the IDE frame keyboard focus, so click
        // once on the empty middle of the header bar first. Nothing there reacts to a single click.
        Dimension screen = Toolkit.getDefaultToolkit().getScreenSize();
        robot.mouseMove(screen.width / 2, HEADER_Y);
        robot.mousePress(InputEvent.BUTTON1_DOWN_MASK);
        robot.mouseRelease(InputEvent.BUTTON1_DOWN_MASK);
        robot.delay(DELAY_MS);
        for (String chord : args) {
            List<Integer> codes = new ArrayList<>();
            for (String name : chord.split("\\+")) {
                codes.add(keyCode(name));
            }
            for (int code : codes) {
                robot.keyPress(code);
            }
            for (int i = codes.size() - 1; i >= 0; i--) {
                robot.keyRelease(codes.get(i));
            }
            robot.delay(DELAY_MS);
        }
        robot.waitForIdle();
    }

    private static int keyCode(String name) throws ReflectiveOperationException {
        String upper = name.toUpperCase();
        upper = switch (upper) {
            case "CTRL" -> "CONTROL";
            case "ESC" -> "ESCAPE";
            default -> upper;
        };
        try {
            return KeyEvent.class.getField("VK_" + upper).getInt(null);
        } catch (NoSuchFieldException e) {
            throw new IllegalArgumentException("Unknown key name: " + name, e);
        }
    }
}
