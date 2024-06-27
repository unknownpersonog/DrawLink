import socket
import json
import tkinter as tk

class DrawingServer:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Drawing Server")
        self.canvas_width = 1280
        self.canvas_height = 720
        self.canvas = tk.Canvas(self.root, width=self.canvas_width, height=self.canvas_height, bg="black")
        self.canvas.pack()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(('0.0.0.0', 12345))
        self.sock.listen(1)

        print("Waiting for connection...")
        self.conn, self.addr = self.sock.accept()
        print(f"Connected by {self.addr}")

        self.conn.setblocking(False)
        self.buffer = ""
        self.last_x = None
        self.last_y = None
        self.root.after(10, self.update_drawing)
        self.root.mainloop()

    def update_drawing(self):
        try:
            data = self.conn.recv(1024).decode()
            self.buffer += data
            while '\n' in self.buffer:
                line, self.buffer = self.buffer.split('\n', 1)
                self.process_data(line)
        except BlockingIOError:
            pass
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            self.root.after(10, self.update_drawing)

    def process_data(self, data):
        try:
            action = json.loads(data)
            action_type = action['type']

            if action_type == 'draw':
                self.handle_draw(action)
            elif action_type == 'erase':
                self.handle_erase(action)
            elif action_type == 'erase_all':
                self.handle_erase_all()
            elif action_type == 'shape':
                self.handle_shape(action)

        except json.JSONDecodeError:
            print("Received invalid JSON data")

    def handle_draw(self, action):
        x = int(action['x'] * self.canvas_width)
        y = int(action['y'] * self.canvas_height)
        is_new_line = action['new_line']
        color = self.rgb_to_hex(action['color'])

        if is_new_line or self.last_x is None or self.last_y is None:
            self.canvas.create_oval(x-1, y-1, x+1, y+1, fill=color, outline=color)
        else:
            self.canvas.create_line(self.last_x, self.last_y, x, y, fill=color, width=2)

        self.last_x, self.last_y = x, y

        if is_new_line:
            self.last_x, self.last_y = None, None

    def handle_erase(self, action):
        x = int(action['x'] * self.canvas_width)
        y = int(action['y'] * self.canvas_height)
        self.canvas.create_oval(x-20, y-20, x+20, y+20, fill="black", outline="black")

    def handle_erase_all(self):
        self.canvas.delete("all")

    def handle_shape(self, action):
        start_x, start_y = action['start']
        end_x, end_y = action['end']
        shape = action['shape']
        color = self.rgb_to_hex(action['color'])

        start_x = int(start_x * self.canvas_width)
        start_y = int(start_y * self.canvas_height)
        end_x = int(end_x * self.canvas_width)
        end_y = int(end_y * self.canvas_height)

        if shape == 'line':
            self.canvas.create_line(start_x, start_y, end_x, end_y, fill=color, width=2)
        elif shape == 'rectangle':
            self.canvas.create_rectangle(start_x, start_y, end_x, end_y, outline=color, width=2)
        elif shape == 'circle':
            center_x = (start_x + end_x) / 2
            center_y = (start_y + end_y) / 2
            radius = ((end_x - start_x)**2 + (end_y - start_y)**2)**0.5 / 2
            self.canvas.create_oval(center_x - radius, center_y - radius, 
                                    center_x + radius, center_y + radius, 
                                    outline=color, width=2)

    def rgb_to_hex(self, rgb):
        return f'#{int(rgb[0]*255):02x}{int(rgb[1]*255):02x}{int(rgb[2]*255):02x}'

if __name__ == '__main__':
    DrawingServer()