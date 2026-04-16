import time

from backend.utils.timing import paced_sleep


def wait_for_element(session, element_id, timeout=8, interval=0.2):
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        try:
            return session.findById(element_id)
        except Exception:
            time.sleep(interval)

    raise Exception(f"Elemento não encontrado: {element_id}")


def wait_until_not_exists(session, element_id, timeout=8):
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        try:
            session.findById(element_id)
            time.sleep(0.2)
        except Exception:
            return True

    return False


def element_exists(session, element_id):
    try:
        session.findById(element_id)
        return True
    except Exception:
        return False


def wait_for_window(session, window_id="wnd[1]", timeout=5):
    return wait_for_element(session, window_id, timeout)


def press_and_wait(session, element_id, wait_id=None, timeout=5):
    session.findById(element_id).press()

    if wait_id:
        return wait_for_element(session, wait_id, timeout)

    paced_sleep(0.5)
    return True


def send_vkey_and_wait(session, window_id, key, wait_id=None, timeout=5):
    session.findById(window_id).sendVKey(key)

    if wait_id:
        return wait_for_element(session, wait_id, timeout)

    paced_sleep(0.5)
    return True
