from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, Line, Ellipse, Rectangle
from kivy.core.window import Window
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.colorpicker import ColorPicker
from kivy.graphics.instructions import InstructionGroup

import socket
import json

class DrawingWidget(Widget):
    def __init__(self, sock, **kwargs):
        super(DrawingWidget, self).__init__(**kwargs)
        self.sock = sock
        self.mode = 'pen'
        self.color = (1, 1, 1, 1)  # Default color: white
        self.shape_start = None
        self.preview = None

    def on_touch_down(self, touch):
        if self.mode == 'eraser':
            self.erase_at_point(touch.x, touch.y)
            self.send_erase_point(touch.x, touch.y)
        elif self.mode in ['line', 'rectangle', 'circle']:
            self.shape_start = (touch.x, touch.y)
            self.preview = InstructionGroup()
            self.canvas.add(self.preview)
            self.update_shape_preview(touch)
        else:  # pen mode
            with self.canvas:
                Color(*self.color)
                touch.ud['line'] = Line(points=(touch.x, touch.y), width=2)
            self.send_normalized_point(touch.x, touch.y, True)

    def on_touch_move(self, touch):
        if self.mode == 'eraser':
            self.erase_at_point(touch.x, touch.y)
            self.send_erase_point(touch.x, touch.y)
        elif self.mode == 'pen':
            touch.ud['line'].points += [touch.x, touch.y]
            self.send_normalized_point(touch.x, touch.y, False)
        elif self.mode in ['line', 'rectangle', 'circle']:
            self.update_shape_preview(touch)

    def on_touch_up(self, touch):
        if self.mode in ['line', 'rectangle', 'circle'] and self.shape_start is not None:
            self.canvas.remove(self.preview)
            with self.canvas:
                Color(*self.color)
                if self.mode == 'line':
                    Line(points=[self.shape_start[0], self.shape_start[1], touch.x, touch.y], width=2)
                elif self.mode == 'rectangle':
                    Line(rectangle=(self.shape_start[0], self.shape_start[1], 
                                    touch.x - self.shape_start[0], touch.y - self.shape_start[1]), width=2)
                elif self.mode == 'circle':
                    center_x = (self.shape_start[0] + touch.x) / 2
                    center_y = (self.shape_start[1] + touch.y) / 2
                    radius = ((touch.x - self.shape_start[0])**2 + (touch.y - self.shape_start[1])**2)**0.5 / 2
                    Line(circle=(center_x, center_y, radius), width=2)
            self.send_shape(self.shape_start, (touch.x, touch.y))
        self.shape_start = None
        self.preview = None

    def update_shape_preview(self, touch):
        if self.preview:
            self.preview.clear()
            color_instruction = Color(*self.color)
            self.preview.add(color_instruction)
            if self.mode == 'line':
                line_instruction = Line(points=[self.shape_start[0], self.shape_start[1], touch.x, touch.y], 
                                        width=2, dash_offset=5, dash_length=10)
                self.preview.add(line_instruction)
            elif self.mode == 'rectangle':
                rect_instruction = Line(rectangle=(self.shape_start[0], self.shape_start[1], 
                                        touch.x - self.shape_start[0], touch.y - self.shape_start[1]), 
                                        width=2, dash_offset=5, dash_length=10)
                self.preview.add(rect_instruction)
            elif self.mode == 'circle':
                center_x = (self.shape_start[0] + touch.x) / 2
                center_y = (self.shape_start[1] + touch.y) / 2
                radius = ((touch.x - self.shape_start[0])**2 + (touch.y - self.shape_start[1])**2)**0.5 / 2
                circle_instruction = Line(circle=(center_x, center_y, radius), 
                                          width=2, dash_offset=5, dash_length=10)
                self.preview.add(circle_instruction)
                
    def erase_at_point(self, x, y):
        with self.canvas:
            Color(0, 0, 0)  # Black color for erasing
            Ellipse(pos=(x - 20, y - 20), size=(40, 40))

    def send_normalized_point(self, x, y, is_new_line):
        norm_x = x / self.width
        norm_y = 1 - (y / self.height)  # Invert y-axis
        data = {
            'type': 'draw',
            'x': norm_x,
            'y': norm_y,
            'new_line': is_new_line,
            'color': self.color
        }
        self.send_data(data)

    def send_erase_point(self, x, y):
        norm_x = x / self.width
        norm_y = 1 - (y / self.height)  # Invert y-axis
        data = {
            'type': 'erase',
            'x': norm_x,
            'y': norm_y
        }
        self.send_data(data)

    def send_shape(self, start, end):
        norm_start_x = start[0] / self.width
        norm_start_y = 1 - (start[1] / self.height)
        norm_end_x = end[0] / self.width
        norm_end_y = 1 - (end[1] / self.height)
        data = {
            'type': 'shape',
            'shape': self.mode,
            'start': (norm_start_x, norm_start_y),
            'end': (norm_end_x, norm_end_y),
            'color': self.color
        }
        self.send_data(data)

    def send_data(self, data):
        if self.sock:
            try:
                self.sock.sendall((json.dumps(data) + '\n').encode())
            except Exception as e:
                print(f"Failed to send data: {e}")

    def clear_canvas(self):
        self.canvas.clear()
        data = {'type': 'erase_all'}
        self.send_data(data)

class DrawingApp(App):
    def build(self):
        self.sock = None
        layout = BoxLayout(orientation='vertical')
        
        ip_layout = BoxLayout(size_hint_y=None, height=50)
        self.ip_input = TextInput(text='localhost', multiline=False)
        connect_button = Button(text='Connect', on_press=self.connect)
        ip_layout.add_widget(self.ip_input)
        ip_layout.add_widget(connect_button)
        
        layout.add_widget(ip_layout)
        
        self.drawing_widget = DrawingWidget(self.sock)
        layout.add_widget(self.drawing_widget)
        
        button_layout = BoxLayout(size_hint_y=None, height=50)
        erase_all_button = Button(text='Erase All', on_press=self.confirm_erase_all)
        color_button = Button(text='Color', on_press=self.show_color_picker)
        pen_button = Button(text='Pen', on_press=lambda x: self.set_mode('pen'))
        eraser_button = Button(text='Eraser', on_press=lambda x: self.set_mode('eraser'))
        line_button = Button(text='Line', on_press=lambda x: self.set_mode('line'))
        rectangle_button = Button(text='Rectangle', on_press=lambda x: self.set_mode('rectangle'))
        circle_button = Button(text='Circle', on_press=lambda x: self.set_mode('circle'))
        
        button_layout.add_widget(erase_all_button)
        button_layout.add_widget(color_button)
        button_layout.add_widget(pen_button)
        button_layout.add_widget(eraser_button)
        button_layout.add_widget(line_button)
        button_layout.add_widget(rectangle_button)
        button_layout.add_widget(circle_button)
        
        layout.add_widget(button_layout)
        
        return layout

    def connect(self, instance):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.ip_input.text, 12345))
            self.drawing_widget.sock = self.sock
            print(f"Connected to {self.ip_input.text}")
        except Exception as e:
            print(f"Failed to connect: {e}")

    def confirm_erase_all(self, instance):
        content = BoxLayout(orientation='vertical')
        content.add_widget(Label(text='Are you sure you want to erase everything?'))
        buttons = BoxLayout(size_hint_y=None, height=40)
        yes_button = Button(text='Yes')
        no_button = Button(text='No')
        buttons.add_widget(yes_button)
        buttons.add_widget(no_button)
        content.add_widget(buttons)

        popup = Popup(title='Confirm Erase All', content=content, size_hint=(None, None), size=(300, 200))
        
        def on_yes(instance):
            self.drawing_widget.clear_canvas()
            popup.dismiss()

        yes_button.bind(on_press=on_yes)
        no_button.bind(on_press=popup.dismiss)

        popup.open()

    def show_color_picker(self, instance):
        color_picker = ColorPicker()
        color_picker.bind(color=self.on_color)
        
        popup = Popup(title='Pick a color', content=color_picker, size_hint=(0.9, 0.9))
        popup.open()

    def on_color(self, instance, value):
        self.drawing_widget.color = value

    def set_mode(self, mode):
        self.drawing_widget.mode = mode

if __name__ == '__main__':
    Window.fullscreen = 'auto'
    DrawingApp().run()