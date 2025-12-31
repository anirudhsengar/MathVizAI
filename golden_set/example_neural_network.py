from manim import *
import numpy as np

class NeuralNetworkViz(Scene):
    def construct(self):
        # 1. Setup
        layers = [4, 6, 6, 2]
        neurons = VGroup()
        connections = VGroup()
        
        # Create Neurons
        for i, layer_size in enumerate(layers):
            layer_neurons = VGroup()
            for j in range(layer_size):
                neuron = Circle(radius=0.15, color=BLUE, fill_opacity=0.8)
                neuron.move_to(RIGHT * (i - 1.5) * 3 + UP * (j - (layer_size - 1) / 2) * 1.2)
                layer_neurons.add(neuron)
            neurons.add(layer_neurons)
            
        # Create Connections
        for i in range(len(layers) - 1):
            layer_connections = VGroup()
            for n1 in neurons[i]:
                for n2 in neurons[i+1]:
                    conn = Line(n1.get_center(), n2.get_center(), stroke_width=1, color=GREY)
                    conn.set_stroke(opacity=0.2)
                    layer_connections.add(conn)
            connections.add(layer_connections)
            
        # 2. Animation Flow
        # Intro
        self.play(LaggedStart(*[FadeIn(layer, shift=DOWN) for layer in neurons], lag_ratio=0.1))
        self.play(LaggedStart(*[Create(conn) for conn in connections], lag_ratio=0.01), run_time=2)
        
        # Pulse Animation
        pulse_group = VGroup()
        for i in range(5): # Create 5 pulses
            start_neuron = neurons[0][np.random.randint(0, layers[0])]
            pulse = Dot(color=YELLOW, radius=0.08)
            pulse.move_to(start_neuron.get_center())
            pulse_group.add(pulse)
            
        self.play(FadeIn(pulse_group))
        
        # Move pulses through network
        for i in range(len(layers) - 1):
            anims = []
            for pulse in pulse_group:
                # Randomly choose next neuron in next layer
                next_neuron = neurons[i+1][np.random.randint(0, layers[i+1])]
                anims.append(pulse.animate.move_to(next_neuron.get_center()))
            
            self.play(*anims, run_time=0.5, rate_func=linear)
            # Flash the neurons they land on
            self.play(*[Flash(pulse, color=YELLOW, flash_radius=0.3) for pulse in pulse_group], run_time=0.3)
            
        self.wait(1)
        
        # Cleanup
        self.play(FadeOut(neurons), FadeOut(connections), FadeOut(pulse_group))
