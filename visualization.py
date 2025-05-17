import pygame
import sys
from class_definition import TransportNet

# count the number of passengers for each destination
def count_destinations(passengers):
    counts = {}
    for p in passengers:
        if p.destination in counts:
            counts[p.destination] += 1
        else:
            counts[p.destination] = 1
    return counts

# display the number of passengers for each destination
def show_destinations(dest_counts, font, surface, position, color):
    x, y = position
    for dest, count in dest_counts.items():
        y += 15
        label = font.render(f"{dest}: {count}", True, color)
        surface.blit(label, (x, y))

def run_with_pygame(tn: TransportNet, until=60):
    pygame.init()
    screen = pygame.display.set_mode((600, 600))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 14)

    # stops_coords = {
    #     "A": (100, 200),
    #     "B": (300, 100),
    #     "C": (500, 200),
    #     "D": (400, 300),
    #     "E": (200, 300),
    #     "F": (200, 450)
    # }
    
    stops_coords = tn.stop_locations 

    # tn.add_bus_line("Line1", ["A","B","C","D","E","F"], ["00:05"], wait_time=5)
    # tn.add_bus_line("Line2", ["F","E","D","C"], ["00:10"], wait_time=3)

    for line in tn.bus_lines:
        for departure in line.schedule:
            tn.env.process(tn.create_vehicle(line, departure))

    tn.env.process(tn.passenger_generator(interval=5))
    tn.env.process(tn.report_status())

    paused = False
    selected_stop = None
    selected_bus = None
    minute = 0

    while minute < until:
        if not paused:
            tn.env.run(until=minute + 1)
            minute += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # click on a stop or vehicle to pause
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos

                # click on a stop
                for name, (x, y) in stops_coords.items():
                    if (mx-x)**2 + (my-y)**2 <= 8**2:
                        selected_stop = name
                        selected_bus = None
                        paused = True
                        break

                # click on a vehicle
                for vehicle in tn.vehicles:
                    x, y = vehicle.get_coordinates()
                    if (mx-x)**2 + (my-y)**2 <= 6**2:
                        selected_bus = vehicle
                        selected_stop = None
                        paused = True
                        break

            # press space to unpause
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                paused = not paused

        # draw the screen
        surface = pygame.Surface((600,600))
        surface.fill((255,255,255))

        # draw the lines
        for start_stop, end_stop, data in tn.graph.edges(data=True):
            color = (0, 0, 0)
            # color busy lines red
            if data.get("busy"):
                color = (255, 0, 0)
            pygame.draw.line(surface, color, stops_coords[start_stop], stops_coords[end_stop], 2)

        # draw the stops
        for name, position in stops_coords.items():
            x, y = position
            pygame.draw.circle(surface, (0,0,255), position, 8)
            label = font.render(f"{name} ({len(tn.passenger_queues.get(name))})", True, (0,0,0))
            surface.blit(label, (x+10, y-15))

            # show destinations for selected stop
            if selected_stop == name:
                count = count_destinations(tn.passenger_queues[name])
                show_destinations(count, font, surface, (position[0] + 10, position[1]), (100, 100, 100))

        # draw the vehicles
        for vehicle in tn.vehicles:
            x, y = vehicle.get_coordinates()

            if vehicle.id.startswith("Line1"):
                color = (255, 0, 0)
            elif vehicle.id.startswith("Line2"):
                color = (0, 255, 0)

            pygame.draw.circle(surface, color, (x,y), 6)
            name = vehicle.id.split("_")[0]
            label = font.render(f"{name}: {len(vehicle.passengers)}", True, (0,0,0))
            surface.blit(label, (x+8, y-5))

            # show destinations for selected bus
            if vehicle == selected_bus:
                count = count_destinations(vehicle.passengers)
                show_destinations(count, font, surface, (x + 8, y - 5), (50, 50, 50))

        screen.blit(surface, (0,0))
        pygame.display.flip()
        clock.tick(2) # 2 FPS

    pygame.quit()

# if __name__ == "__main__":
#     tn = TransportNet()

#     tn.add_connection("A","B",5)
#     tn.add_connection("B","C",7)
#     tn.add_connection("C","D",4,busy=True)
#     tn.add_connection("D","E",6)
#     tn.add_connection("E","A",5)
#     tn.add_connection("E","F",8)

#     run_with_pygame(tn, until=60*24)